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


    def router_tasks(self):
        @self.router.post("/rooms", response_class=HTMLResponse)
        async def fetch_rooms(request: Request, session_token: str = Form(...), group_id: str = Form(...)):
            await self.worker_session(self.__fetch_rooms(session_token, group_id)) #this might not work as expected.