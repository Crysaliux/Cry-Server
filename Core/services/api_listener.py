from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from ..services.worker import Client, Group, Space, Room, Message, Role, RoleToRoomPerms
from sqlalchemy import insert, select, update, delete
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from ..components import *
from .validators import *

class GroupRelated(BaseModel):
    group_id: str

class RoomRelated(BaseModel):
    group_id: str
    room_id: str

class RoleRelated(BaseModel):
    group_id: str
    room_id: str
    role_id: str


class APIListener:
    def __init__(
            self,
            oauth2,
            worker_session,
            algorithm,
            perms,
            message_load_batch_size: int,
        ):
        self.oauth2 = oauth2
        self.worker_session = worker_session
        self.algorithm = algorithm
        self.perms = perms
        self.message_load_batch_size = message_load_batch_size
        self.router = APIRouter()

        self.api_call_bindings = {
            "fetch_groups": self.__fetch_groups,
            "fetch_rooms": self.__fetch_rooms,
            "fetch_group": self.__fetch_group,
            "fetch_members": self.__fetch_members,
            "fetch_roles": self.__fetch_roles,
            "fetch_messages": self.__fetch_messages,
            "fetch_permstable": self.__fetch_permstable,
        }
        self.__register_api_call_handlers()

    def __register_api_call_handlers(self):
        for api_call, handler in self.api_call_bindings.items():
            setattr(self, f"__call_{api_call}", self.worker_session(handler))

    def __emit_api_error(index: str, target: str):
        return {
            "status": False, 
            "body": None, 
            "error": {"index": index, "target": target},
        }
    

    async def __fetch_groups(self, session_token: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(session_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

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
            
        return {
            "status": True, 
            "body": groups, 
            "error": None,
        }

    async def __fetch_rooms(self, session_token: str, group_id: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(session_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.rooms),
            selectinload(Group.spaces),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        body = {
            "spaces": [],
            "rooms": [],
        }
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permissions_all("VIEW_ROOMS"):
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
            return {
                "status": True, 
                "body": body, 
                "error": None,
            }
        
        return self.__emit_api_error("MISSING_PERMISSION", "VIEW_ROOMS")

    async def __fetch_group(self, session_token: str, group_id: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(session_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.rooms),
            selectinload(Group.spaces),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        body = {
            "spaces": [],
            "rooms": [],
            "members": [],
            "primary_channel_messages": [],
            "primary_channel_id": None,
        }
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permissions_all("VIEW_ROOMS"):
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

            return {
                "status": True, 
                "body": body, 
                "error": None,
            }
        
        return self.__emit_api_error("MISSING_PERMISSION", "VIEW_ROOMS")

    async def __fetch_members(self, session_token: str, group_id: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, _ = valid.session_is_valid(session_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        members = []

        for member in group.members:
            members.append({"nickname": member.nickname, "id": member.id})

        return {
            "status": True, 
            "body": members, 
            "error": None,
        }
    
    async def __fetch_roles(self, session_token: str, group_id: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(session_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        roles = []
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permissions_all("MANAGE_ROLES"):
            
            for role in group.roles:
                roles.append({
                    "group_id": group_id,
                    "name": role.name,
                    "color": role.color,
                    "global_permissions": perm_valid.unmask_global_permissions(role.global_permissions),
                    "id": role.id,
                })

            return {
                "status": True, 
                "body": roles, 
                "error": None,
            }
        
        return await self.__emit_api_error("MISSING_PERMISSION", "MANAGE_ROLES")

    async def __fetch_messages(self, session_token: str, group_id: str, room_id: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(session_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        room_res = await session.execute(select(Room).options(
            selectinload(Room.messages),
        ).where(Room.id == room_id))
        room = room_res.scalar_one_or_none()

        if not group:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "group")

        if not room:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "room")
        
        messages = []
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permissions_all("VIEW_ROOMS") or \
        perm_valid.has_room_permissions_all("VIEW_ROOM"):
            
            for message in room.messages[-self.message_load_batch_size:]:
                messages.append({
                    "client_id": client.id,
                    "nickname": client.nickname,
                    "content": message.content,
                    "id": message.id,
                })

            return {
                "status": True, 
                "body": messages, 
                "error": None,
            }
        
        return self.__emit_api_error("MISSING_PERMISSION", "VIEW_ROOMS")
    
    async def __fetch_permstable(self, session_token: str, group_id: str, room_id: str, role_id: str, session):
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(session_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_SESSION_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        rtr_res = await session.execute(select(RoleToRoomPerms).where(
            RoleToRoomPerms.role_id == role_id,
            RoleToRoomPerms.room_id == room_id,
        ))
        rtr = rtr_res.scalar_one_or_none()

        if not group:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        if not rtr:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "permissions table")
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permissions_all("MANAGE_ROLES"):

            return {
                "status": True, 
                "body": {
                    "permissions": perm_valid.unmask_room_permissions(rtr.permissions),
                    "id": rtr.id,
                }, 
                "error": None,
            }
        
        return self.__emit_api_error("MISSING_PERMISSION", "MANAGE_ROLES")
    

    def router_tasks(self):
        @self.router.post("/fetch_groups")
        async def fetch_groups(request: Request, session_token: str = Depends(self.oauth2)):
            return await self.__call_fetch_groups(session_token)

        @self.router.post("/fetch_rooms")
        async def fetch_rooms(request: Request, payload: GroupRelated, session_token: str = Depends(self.oauth2)):
            return await self.__call_fetch_rooms(session_token, payload.group_id)

        @self.router.post("/fetch_group")
        async def fetch_group(request: Request, payload: GroupRelated, session_token: str = Depends(self.oauth2)):
            return await self.__call_fetch_group(session_token, payload.group_id)

        @self.router.post("/fetch_members")
        async def fetch_members(request: Request, payload: GroupRelated, session_token: str = Depends(self.oauth2)):
            return await self.__call_fetch_members(session_token, payload.group_id)

        @self.router.post("/fetch_roles")
        async def fetch_roles(request: Request, payload: GroupRelated, session_token: str = Depends(self.oauth2)):
            return await self.__call_fetch_roles(session_token, payload.group_id)

        @self.router.post("/fetch_messages")
        async def fetch_messages(request: Request, payload: RoomRelated, session_token: str = Depends(self.oauth2)):
            return await self.__call_fetch_messages(session_token, payload.group_id, payload.room_id)
        
        @self.router.post("/fetch_permstable")
        async def fetch_permstable(request: Request, payload: RoleRelated, session_token: str = Depends(self.oauth2)):
            return await self.__call_fetch_permstable(session_token, payload.group_id, payload.room_id, payload.role_id)