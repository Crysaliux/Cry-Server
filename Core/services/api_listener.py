from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from ..services.worker import Client, Group, Space, Room, Message, Role, RoleToRoomPerms
from sqlalchemy import insert, select, update, delete
from sqlalchemy.orm import selectinload
from ..components import *
from .validators import *

class APIListener:
    def __init__(
            self,
            worker_session,
            algorithm,
            perms,
        ):
        self.worker_session = worker_session
        self.algorithm = algorithm
        self.perms = perms
        self.router = APIRouter()

        self.api_call_bindings = {
            "fetch_groups": self.__fetch_groups,
            "fetch_rooms": self.__fetch_rooms,
            "fetch_group": self.__fetch_group,
        }
        self.__register_api_call_handlers()

    def __register_api_call_handlers(self):
        for api_call, handler in self.api_call_bindings.items():
            setattr(self, f"__call_{api_call}", self.worker_session(handler))

    async def __emit_api_error(index: str, target: str):
        return JSONResponse(content={
            "status": False, 
            "body": None, 
            "error": {"index": index, "target": target},
        }, status_code=201)
    

    async def __fetch_groups(self, session_token: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(session_token, session)

        if not status:
            await self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

        extra_client_res = await session.execute(select(Client).options(
            selectinload(Client.groups),
        ).where(Client.id == client.id))
        extra_client = extra_client_res.scalar_one_or_none()
        
        groups = []
        
        for group in extra_client.groups:
            groups.append({
                "name": group.name,
                "about_group": group.about_group,
                "icon_url": group.icon_url,
                "nsfw": group.nsfw,
                "id": group.id,

                "content_filter": group.content_filter,
                "content_filter_level": group.content_filter_level,
            })
            
        return JSONResponse(content={
            "status": True, 
            "body": groups, 
            "error": None,
        }, status_code=201)

    async def __fetch_rooms(self, session_token: str, group_id: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(session_token, session)

        if not status:
            await self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.rooms),
            selectinload(Group.spaces),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        body = {
            "spaces": [],
            "rooms": [],
        }
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permission("VIEW_ROOMS"):
            for space in group.spaces:
                body["spaces"].append({"group_id": group_id, "name": space.name, "id": space.id})
            for room in group.rooms:
                if perm_valid.has_room_permission("VIEW_ROOM", room.id):
                    body["rooms"].append({
                        "group_id": group_id, 
                        "space_id": room.space_id, 
                        "name": room.name, 
                        "about_room": room.about_room, 
                        "nsfw": room.nsfw, 
                        "id": room.id
                    })
            return JSONResponse(content={
                "status": True, 
                "body": body, 
                "error": None,
            }, status_code=201)
        
        await self.__emit_api_error("MISSING_PERMISSION", "VIEW_ROOMS")

    async def __fetch_group(self, session_token: str, group_id: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(session_token, session)

        if not status:
            await self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.rooms),
            selectinload(Group.spaces),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        body = {
            "spaces": [],
            "rooms": [],
            "members": [],
            "primary_channel_messages": [],
            "primary_channel_id": None,
        }
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permission("VIEW_ROOMS"):
            first_room = group.rooms[0]

            for space in group.spaces:
                body["spaces"].append({"group_id": group_id, "name": space.name, "id": space.id})

            for room in group.rooms:
                if perm_valid.has_room_permission("VIEW_ROOM", room.id):
                    body["rooms"].append({
                        "group_id": group_id, 
                        "space_id": room.space_id, 
                        "name": room.name, 
                        "about_room": room.about_room, 
                        "nsfw": room.nsfw, 
                        "id": room.id,
                    })

            for member in group.members:
                body["members"].append({
                    "nickname": member.nickname, 
                    "id": member.id, 
                })

            for message in first_room:
                body["primary_channel_messages"].append({
                    "client_id": message.author.id, 
                    "nickname": message.author.nickname,
                    "content": message.content,
                    "id": message.id, 
                })

            body["primary_channel_id"] = first_room.id

            return JSONResponse(content={
                "status": True, 
                "body": body, 
                "error": None,
            }, status_code=201)
        
        await self.__emit_api_error("MISSING_PERMISSION", "VIEW_ROOMS")

    async def __fetch_members(self, session_token: str, group_id: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, _ = valid.session_is_valid(session_token, session)

        if not status:
            await self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        members = []

        for member in group.members:
            members.append({"nickname": member.nickname, "id": member.id})

        return JSONResponse(content={
            "status": True, 
            "body": members, 
            "error": None,
        }, status_code=201)
    
    async def __fetch_roles(self, session_token: str, group_id: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(session_token, session)

        if not status:
            await self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        roles = []
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permission("MANAGE_ROLES"):
            
            for role in group.roles:
                roles.append({
                    "group_id": group_id,
                    "name": role.name,
                    "color": role.color,
                    #"global_permissions": perm_valid. to finish today + {"index": ..., "target": ...} error for frontend.
                })

            

            return JSONResponse(content={
                "status": True, 
                "body": roles, 
                "error": None,
            }, status_code=201)
        
        await self.__emit_api_error("MISSING_PERMISSION", "MANAGE_ROLES")
    

    def router_tasks(self):
        @self.router.post("/fetch_groups", response_class=HTMLResponse)
        async def fetch_groups(request: Request, session_token: str = Form(...)):
            await self.__call_fetch_groups(session_token)

        @self.router.post("/fetch_rooms", response_class=HTMLResponse)
        async def fetch_rooms(request: Request, session_token: str = Form(...), group_id: str = Form(...)):
            await self.__call_fetch_rooms(session_token, group_id)

        @self.router.post("/fetch_group", response_class=HTMLResponse)
        async def fetch_group(request: Request, session_token: str = Form(...), group_id: str = Form(...)):
            await self.__call_fetch_group(session_token, group_id)