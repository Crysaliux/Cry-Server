from fastapi import FastAPI, Request, Form, WebSocket, Header, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from ..services.worker import Client, Group, Space, Room, Message, Role, RoleToRoomPerms
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import insert, select, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import or_
from pydantic import BaseModel
from typing import Literal, TypeAlias
from ..components import *
from .validators import *
from functools import wraps
from logging import log
import aiofiles
import uuid

class GroupRelated(BaseModel):
    group_id: str

class PrimaryCheckRelated(BaseModel):
    group_global_name: str

class GroupFetchRelated(BaseModel):
    group_global_name: str
    room_id: str

class RoomRelated(BaseModel):
    group_id: str
    room_id: str

class RoleRelated(BaseModel): #Rethink & Refactor!
    group_id: str
    room_id: str
    role_id: str


#Emission types
EmitError: TypeAlias = dict[str, Literal[False] | None | dict[str, str]]
EmitCommon: TypeAlias = dict[str, bool | list[str, str | bool | int] | str | None]


class APIListener:
    def __init__(
            self,
            oauth2,
            session,
            ws,
            logger,
            algorithm,
            perms,
            addr,
            message_load_batch_size: int,
            access_key,
            client_server_origin,
            storage_images_path,
            storage_files_path,

        ):
        self.oauth2 = oauth2
        self.session = session
        self.ws = ws
        self.logger = logger
        self.algorithm = algorithm
        self.perms = perms
        self.addr = addr
        self.message_load_batch_size = message_load_batch_size
        self.access_key = access_key
        self.client_server_origin = client_server_origin
        self.storage_images_path = storage_images_path
        self.storage_files_path = storage_files_path

        self.router = APIRouter()

        self.api_call_bindings = {
            "fetch_groups": self.__fetch_groups,
            "fetch_rooms": self.__fetch_rooms,
            "fetch_group": self.__fetch_group,
            "fetch_members": self.__fetch_members,
            "fetch_roles": self.__fetch_roles,
            "fetch_messages": self.__fetch_messages,
            "fetch_permstable": self.__fetch_permstable,
            "get_primary_room": self.__get_primary_room,
            "check_global_name": self.__check_global_name,
            "upload_attachement": self.__upload_attachement,
        }
        self.__register_api_call_handlers()

    def __register_api_call_handlers(self) -> None:
        for api_call, handler in self.api_call_bindings.items():
            setattr(self, f"_call_{api_call}", self.ws(handler, self.session))

    def __emit_api_error(self, index: str, target: str) -> EmitError:
        return {
            "status": False, 
            "body": None, 
            "error": {"index": index, "target": target},
        }
    

    async def __fetch_groups(self, access_token: str, session) -> EmitError | EmitCommon:
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = await valid.access_token_is_valid(access_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_ACCESS_TOKEN", "client")

        extra_client_res = await session.execute(select(Client).options(
            selectinload(Client.groups),
        ).where(Client.id == client.id))
        extra_client = extra_client_res.scalar_one_or_none()
        
        groups = []
        
        for group in extra_client.groups:
            groups.append({
                "name": group.name,
                "global_name": group.global_name,
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

    async def __fetch_rooms(self, access_token: str, group_id: str, session) -> EmitError | EmitCommon:
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = await valid.access_token_is_valid(access_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_ACCESS_TOKEN", "client")

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
        perm_valid.has_global_permissions_all(["VIEW_ROOMS"]):
            for space in group.spaces:
                body["spaces"].append({"group_id": group_id, "name": space.name, "id": space.id})
            for room in group.rooms:
                if perm_valid.has_room_permissions_all(room.id, ["VIEW_ROOM"]):
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

    async def __fetch_group(self, access_token: str, group_global_name: str, room_id: str, session) -> EmitError | EmitCommon:
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = await valid.access_token_is_valid(access_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_ACCESS_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.rooms),
            selectinload(Group.spaces),
            selectinload(Group.members),
        ).where(Group.global_name == group_global_name))
        group = group_res.scalar_one_or_none()

        room_res = await session.execute(select(Room).options(
            selectinload(Room.messages),
        ).where(Room.id == room_id))
        room = room_res.scalar_one_or_none()

        if not group:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        if not room:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "room")
             
        body = {
            "self": {
                "name": group.name,
                "global_name": group.global_name,
                "about_group": group.about_group,
                "icon_url": group.icon_url,
                "nsfw": group.nsfw,
                "id": group.id,

                "content_filter": group.content_filter,
                "content_filter_level": group.content_filter_level,
            },
            "spaces": [],
            "rooms": [],
            "members": [],
            "primary_room_messages": [],
        }
        
        perm_valid = PermissionValidator(client, group, self.perms)
        
        owner = group.owner.id == client.id
        if owner or \
        (perm_valid.has_global_permissions_all(["VIEW_ROOMS"]) and perm_valid.has_room_permissions_all(room.id, ["VIEW_ROOM"])):
            for space in group.spaces:
                body["spaces"].append({"group_id": group.id, "name": space.name, "id": space.id})

            for room in group.rooms:
                if perm_valid.has_room_permissions_all(room.id, ["VIEW_ROOM"]) or owner:
                    body["rooms"].append({
                        "group_id": group.id, 
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

            for message in room.messages:
                body["primary_room_messages"].append({
                    "author_id": message.author.id, 
                    "nickname": message.author.nickname,
                    "content": message.content,
                    "sent_at": message.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "id": message.id, 
                })


            return {
                "status": True, 
                "body": body, 
                "error": None,
            }
        
        return self.__emit_api_error("MISSING_PERMISSION", "VIEW_ROOMS")

    async def __fetch_members(self, access_token: str, group_id: str, session) -> EmitError | EmitCommon:
        valid = ClientValidator(self.access_key, self.algorithm)
        status, _ = await valid.access_token_is_valid(access_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_ACCESS_TOKEN", "client")

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
    
    async def __fetch_roles(self, access_token: str, group_id: str, session) -> EmitError | EmitCommon:
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = await valid.access_token_is_valid(access_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_ACCESS_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        roles = []
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permissions_all(["MANAGE_ROLES"]):
            
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

    async def __fetch_messages(self, access_token: str, group_id: str, room_id: str, session) -> EmitError | EmitCommon:
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = await valid.access_token_is_valid(access_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_ACCESS_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        room_res = await session.execute(select(Room).options(
            selectinload(Room.messages),
        ).where(Room.id == room_id, Room.group_id == group_id))
        room = room_res.scalar_one_or_none()

        if not group:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "group")

        if not room:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "room")
        
        messages = []
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permissions_all(["VIEW_ROOMS"]) or \
        perm_valid.has_room_permissions_all(room.id, ["VIEW_ROOM"]):
            
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
    
    async def __fetch_permstable(self, access_token: str, group_id: str, room_id: str, role_id: str, session) -> EmitError | EmitCommon:
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = await valid.access_token_is_valid(access_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_ACCESS_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        rtr_res = await session.execute(select(RoleToRoomPerms).where(
            RoleToRoomPerms.role_id == role_id,
            RoleToRoomPerms.room_id == room_id,
            RoleToRoomPerms.group_id == group_id,
        ))
        rtr = rtr_res.scalar_one_or_none()

        if not group:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        if not rtr:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "permissions table")
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permissions_all(["MANAGE_ROLES"]):

            return {
                "status": True, 
                "body": {
                    "group_id": group_id,
                    "permissions": perm_valid.unmask_room_permissions(rtr.permissions),
                    "id": rtr.id,
                }, 
                "error": None,
            }
        
        return self.__emit_api_error("MISSING_PERMISSION", "MANAGE_ROLES")
    
    async def __get_primary_room(self, access_token: str, group_global_name: str, session) -> EmitError | EmitCommon:
        valid = ClientValidator(self.access_key, self.algorithm, self.logger)
        status, client = await valid.access_token_is_valid(access_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_ACCESS_TOKEN", "client")

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.rooms),
        ).where(Group.global_name == group_global_name))
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__emit_api_error("OBJECT_NON_EXISTANT", "group")
        
        perm_valid = PermissionValidator(client, group, self.perms)
        
        owner = group.owner.id == client.id
        if owner or \
        perm_valid.has_global_permissions_all(["VIEW_ROOMS"]):
            room_id = None

            for room in group.rooms:
                if room_id: break
                if perm_valid.has_room_permissions_all(room.id, ["VIEW_ROOM"]) or owner:
                    room_id = room.id

            return {
                "status": True, 
                "body": {
                    "room_id": room_id,
                }, 
                "error": None,
            }
        
        return self.__emit_api_error("MISSING_PERMISSION", "VIEW_ROOMS")
    
    async def __check_global_name(self, access_token: str, group_global_name: str, session) -> EmitError | EmitCommon:
        valid = ClientValidator(self.access_key, self.algorithm, self.logger)
        status, _ = await valid.access_token_is_valid(access_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_ACCESS_TOKEN", "client")

        exists = False

        global_name_check_res = await session.execute(select(Group).where(Group.global_name == group_global_name))
        global_name_check = global_name_check_res.scalar_one_or_none()

        if global_name_check:
            exists = True
        
        return {
            "status": True, 
            "body": {
                "exists": exists,
            }, 
            "error": None,
        }
    
    async def __upload_attachement(self, access_token: str, file: UploadFile, session) -> EmitError | EmitCommon:
        valid = ClientValidator(self.access_key, self.algorithm, self.logger)
        status, _ = await valid.access_token_is_valid(access_token, session)

        if not status:
            return self.__emit_api_error("INVALID_OR_EXPIRED_ACCESS_TOKEN", "client")

        filename = f"{uuid.uuid4()}.{file.filename.split(".")[-1]}"
        data = await file.read()
        
        if file.content_type.startswith("image/"):
            save_to = f"{self.storage_images_path}/{filename}"
            file_url = f"http://{self.addr[0]}:{self.addr[1]}/images/{filename}"
        else:
            save_to = f"{self.storage_files_path}/{filename}"
            file_url = f"http://{self.addr[0]}:{self.addr[1]}/files/{filename}"

        try:
            async with aiofiles.open(save_to, "wb") as buffer:
                await buffer.write(data)
        except:
            return self.__emit_api_error("FAILED_TO_SAVE_ATTACHEMENT", f"{file.filename}") #original filename
        
        return {
            "status": True, 
            "body": {
                "file_url": file_url,
            }, 
            "error": None,
        }
    

    def router_tasks(self):
        @self.router.post("/fetch_groups")
        async def fetch_groups(request: Request, authorization: str = Header(...)):
            access_token = authorization.replace("Bearer", "").strip()
            return await self._call_fetch_groups(access_token)

        @self.router.post("/fetch_rooms")
        async def fetch_rooms(request: Request, payload: GroupRelated, authorization: str = Header(...)):
            access_token = authorization.replace("Bearer", "").strip()
            return await self._call_fetch_rooms(access_token, payload.group_id)

        @self.router.post("/fetch_group")
        async def fetch_group(request: Request, payload: GroupFetchRelated, authorization: str = Header(...)):
            access_token = authorization.replace("Bearer", "").strip()
            return await self._call_fetch_group(access_token, payload.group_global_name, payload.room_id)

        @self.router.post("/fetch_members")
        async def fetch_members(request: Request, payload: GroupRelated, authorization: str = Header(...)):
            access_token = authorization.replace("Bearer", "").strip()
            return await self._call_fetch_members(access_token, payload.group_id)

        @self.router.post("/fetch_roles")
        async def fetch_roles(request: Request, payload: GroupRelated, authorization: str = Header(...)):
            access_token = authorization.replace("Bearer", "").strip()
            return await self._call_fetch_roles(access_token, payload.group_id)

        @self.router.post("/fetch_messages")
        async def fetch_messages(request: Request, payload: RoomRelated, authorization: str = Header(...)):
            access_token = authorization.replace("Bearer", "").strip()
            return await self._call_fetch_messages(access_token, payload.group_id, payload.room_id)
        
        @self.router.post("/fetch_permstable")
        async def fetch_permstable(request: Request, payload: RoleRelated, authorization: str = Header(...)):
            access_token = authorization.replace("Bearer", "").strip()
            return await self._call_fetch_permstable(access_token, payload.group_id, payload.room_id, payload.role_id)
        
        @self.router.post("/get_primary_room")
        async def get_primary_room(request: Request, payload: PrimaryCheckRelated, authorization: str = Header(...)):
            access_token = authorization.replace("Bearer", "").strip()
            return await self._call_get_primary_room(access_token, payload.group_global_name)
        
        @self.router.post("/check_global_name")
        async def check_global_name(request: Request, payload: PrimaryCheckRelated, authorization: str = Header(...)):
            access_token = authorization.replace("Bearer", "").strip()
            return await self._call_check_global_name(access_token, payload.group_global_name)
        
        @self.router.post("/upload_attachement")
        async def upload_attachement(request: Request, file: UploadFile = File(...), authorization: str = Header(...)):
            access_token = authorization.replace("Bearer", "").strip()
            return await self._call_upload_attachement(access_token, file)