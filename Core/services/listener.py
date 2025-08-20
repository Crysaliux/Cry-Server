from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal
from ..services.worker import Client, Group, Space, Room, Message, Role, RoleToRoomPerms
from sqlalchemy import insert, select, update, delete
from sqlalchemy.orm import selectinload
from ast import literal_eval
from datetime import datetime
from ..components import *
from .validators import *
from PIL import Image
import aiofiles
import socketio
import asyncio
import json
import time
import jwt
import io
import os


class Listener:
    def __init__(
            self, 
            hasher, 
            worker_session,  
            oauth2,
            storage_images_path: str, 
            storage_files_path: str, 
            max_message_length: dict, 
            max_image_size: int, 
            max_file_size: dict, 
            client_server_origin: str, 
            heartbeat_interval: int,
            algorithm, access_key, 
            addr: tuple, 
            gateway: socketio.AsyncServer,
            perms,
            tepmlates: Jinja2Templates,
        ):
        self.addr = addr
        self.access_key = access_key
        self.hasher = hasher
        self.worker_session = worker_session
        self.oauth2 = oauth2
        self.storage_images_path = storage_images_path
        self.storage_files_path = storage_files_path
        self.max_message_length = max_message_length
        self.max_image_size = max_image_size
        self.max_file_size = max_file_size
        self.client_server_origin = client_server_origin
        self.templates = tepmlates
        self.heartbeat_interval = heartbeat_interval
        self.algorithm = algorithm
        self.gateway = gateway
        self.perms = perms
        self.router = APIRouter()

        self.event_bindings = {
            "connect": self.__on_connect,
            "disconnect": self.__on_disconnect,

            "create_group": self.__on_create_group,
            "create_space": self.__on_create_space,
            "create_room": self.__on_create_room,
            "send_message": self.__on_send_message,
            "create_role": self.__on_create_role,
            "create_permissions_table": self.__on_create_permissions_table,

            "update_client": self.__on_update_client,
            "update_group": self.__on_update_group,
            "update_space": self.__on_update_space,
            "update_room": self.__on_update_room,
            "edit_message": self.__on_edit_message,
            "update_role": self.__on_update_role,
            "update_permissions_table": self.__on_update_permissions_table,

            "delete_client": self.__on_delete_client,
            "delete_group": self.__on_delete_group,
            "delete_space": self.__on_delete_space,
            "delete_room": self.__on_delete_room,
            "delete_message": self.__on_delete_message,
            "delete_role": self.__on_delete_role,
            "delete_permissions_table": ..., # why? Idk
        }
        self.__register_event_handlers()

    def __register_event_handlers(self):
        for event, handler in self.event_bindings.items():
            self.gateway.on(event, self.worker_session(handler))

    async def __emit_error(self, sid, id: int, event: str, error: dict):
        await self.gateway.emit(event, {
            "status": False,
            "body": {"id": id},
            "error": error,
        }, to=sid)

#Listener module's main body
    async def __on_connect(self, sid, eviron, auth, session):
        session_token = auth["session_token"]
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(session_token, session)

        if not status:
            raise ConnectionRefusedError("INVALID_OR_EXPIRED_SESSION_TOKEN")
        
        await self.gateway.save_session(sid, {"client": client, "session_token": session_token})

    async def __on_disconnect(self, sid):
        ...

    #ON_CREATE_...
    async def __on_create_group(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "group_created", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "group_created", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, CreateGroup):
            await self.__emit_error(sid, id, "group_created", {"index": "WRONG_REQUEST", "target": "group"})
            return

        name, about_group, icon_url, id = body.name, body.about_group, body.icon_url, body.id

        session.add(Group(owner_id=client.id, name=name, about_group=about_group, icon_url=icon_url, id=id)) 
        await session.commit()

        await self.gateway.emit("group_created", {
            "status": True,
            "body": {"id": id},
            "error": None,
        }, to=sid)

    async def __on_create_space(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "space_created", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "space_created", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, CreateSpace):
            await self.__emit_error(sid, id, "space_created", {"index": "WRONG_REQUEST", "target": "space"})
            return

        group_id, name, id = body.group_id, body.name, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "space_created", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "space_created", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_SPACES"]):
            session.add(Space(group_id=group_id, creator_id=client.id, name=name, id=id)) 
            await session.commit()
            
            await self.gateway.emit("space_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, id, "space_created", {"index": "MISSING_PERMISSION", "target": "MANAGE_SPACES"})

    async def __on_create_room(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "room_created", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "room_created", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, CreateRoom):
            await self.__emit_error(sid, id, "room_created", {"index": "WRONG_REQUEST", "target": "room"})
            return

        group_id, space_id, name, about_room, id = body.group_id, body.space_id, body.name, body.about_room, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "room_created", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "room_created", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROOMS"]):
            session.add(Room(group_id=group_id, space_id=space_id, creator_id=client.id, name=name, about_room=about_room, id=id)) 
            await session.commit()

            await self.gateway.emit("room_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, id, "room_created", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROOMS"})

    async def __on_send_message(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "message_sent", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "message_sent", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, SendMessage):
            await self.__emit_error(sid, id, "message_sent", {"index": "WRONG_REQUEST", "target": "message"})
            return

        group_id, room_id, content, id = body.group_id, body.room_id, body.content, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "message_sent", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "message_sent", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)

        if perm_valid.global_validity(["CO_OWNER", "SEND_MESSAGES"]) or \
        perm_valid.has_room_permissions_all(room_id, ["SEND_MESSAGES"]):
            session.add(Message(group_id=group_id, room_id=room_id, author_id=client.id, content=content, id=id)) 
            await session.commit()

            await asyncio.gather(
                self.gateway.emit("message_sent", {
                    "status": True, 
                    "body": {
                        "client_id": client.id,
                        "nickname": client.nickname, 
                        "content": content, 
                        "id": id
                    }, 
                    "error": None
                }, room=f"#{room_id}"),

                self.gateway.emit("message_sent_notif", {
                    "group_id": group_id,
                    "room_id": room_id, 
                    "nickname": client.nickname,
                    "content": content,
                }, room=f"${group_id}"),
            )
        else:
            await self.__emit_error(sid, id, "message_sent", {"index": "MISSING_PERMISSION", "target": "SEND_MESSAGES"})
    
    async def __on_create_role(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "role_created", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "role_created", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, CreateRole):
            await self.__emit_error(sid, id, "role_created", {"index": "WRONG_REQUEST", "target": "role"})
            return

        group_id, name, id = body.group_id, body.name, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "role_created", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "role_created", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROLES"]):
            session.add(Role(group_id=group_id, name=name, id=id))
            await session.commit()
            await self.gateway.emit("role_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, id, "role_created", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROLES"})

    async def __on_create_permissions_table(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "permissions_table_created", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "permissions_table_created", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, CreatePermissionsTable):
            await self.__emit_error(sid, id, "permissions_table_created", {"index": "WRONG_REQUEST", "target": "permissions_table"})
            return

        group_id, role_id, room_id, permissions, id = body.group_id, body.role_id, body.room_id, body.permissions, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "permissions_table_created", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "permissions_table_created", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROLES"]):
            session.add(RoleToRoomPerms(role_id=role_id, room_id=room_id, permissions=perm_valid.mask_room_permissions(permissions), id=id))
            await session.commit()
            await self.gateway.emit("permissions_table_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, id, "permissions_table_created", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROLES"})

    #ON_UPDATE_...
    async def __on_update_client(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "client_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "client_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, UpdateClient):
            await self.__emit_error(sid, id, "client_updated", {"index": "WRONG_REQUEST", "target": "client"})
            return

        username, nickname, about_me, avatar_url, color_theme = body.username, body.nickname, body.about_me, body.avatr_url, body.color_theme

        username_check_res = await session.execute(select(Client).where(Client.username == username))
        username_check = username_check_res.scalar_one_or_none()

        if username_check:
            await self.__emit_error(sid, client.id, "client_updated", {"index": "USERNAME_EXISTS", "target": "client"})
            return

        update_status_res = await session.execute(update(Client).where(Client.id == client.id).values(username=username, nickname=nickname, about_me=about_me, avatar_url=avatar_url, color_theme=color_theme).returning(Client.id))
        update_status = update_status_res.scalar_one_or_none()
        if update_status:
            client_updated_res = await session.execute(select(Client).options(
                selectinload(Client.groups),
            ).where(Client.id == client.id))
            client_updated = client_updated_res.scalar_one_or_none()

            if not client_updated:
                await self.__emit_error(sid, client.id, "client_updated", {"index": "UPDATE_FAILED", "target": "client"})
                return
            
            await self.gateway.save_session(sid, {"client": client_updated})

            emits = [
                self.gateway.emit("client_updated", {
                    "status": True, 
                    "body": {
                        "username": username,
                        "nickname": nickname, 
                        "avatar_url": avatar_url, 
                        "id": client.id,
                    },
                    "error": None,
                }, room=f"${group.id}")
                for group in client.groups
            ]
            emits.append(
                self.gateway.emit("client_updated", {
                    "status": True, 
                    "body": {"id": client.id},
                    "error": None,
                }, room=sid)
            )
            await asyncio.gather(*emits)
        else:
            await self.__emit_error(sid, client.id, "client_updated", {"index": "UPDATE_FAILED", "target": "client"})

    async def __on_update_group(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "group_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "group_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, UpdateGroup):
            await self.__emit_error(sid, id, "group_updated", {"index": "WRONG_REQUEST", "target": "group"})
            return

        name, about_group, icon_url, nsfw, content_filter, content_filter_level, id = body.owner_id, body.name, body.about_group, body.icon_url, body.nsfw, body.content_filter, body.content_filter_level, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "group_updated", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "group_updated", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_GROUP"]):
            update_status_res = await session.execute(update(Group).where(Group.id == id).values(name=name, about_group=about_group, icon_url=icon_url, nsfw=nsfw, content_filter=content_filter, content_filter_level=content_filter_level).returning(Group.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("group_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${id}")
            else:
                await self.__emit_error(sid, id, "group_updated", {"index": "UPDATE_FAILED", "target": "group"})
        else:
            await self.__emit_error(sid, id, "group_updated", {"index": "MISSING_PERMISSION", "target": "MANAGE_GROUP"})
    
    async def __on_update_space(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "space_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "space_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, UpdateSpace):
            await self.__emit_error(sid, id, "space_updated", {"index": "WRONG_REQUEST", "target": "space"})
            return

        group_id, name, id = body.group_id, body.creator_id, body.name, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "space_updated", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "space_updated", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_SPACES"]):
            update_status_res = await session.execute(update(Space).where(Space.id == id).values(name=name).returning(Space.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("space_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "space_updated", {"index": "UPDATE_FAILED", "target": "space"})
        else:
            await self.__emit_error(sid, id, "space_updated", {"index": "MISSING_PERMISSION", "target": "MANAGE_SPACES"})
    
    async def __on_update_room(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "room_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "room_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, UpdateRoom):
            await self.__emit_error(sid, id, "room_updated", {"index": "WRONG_REQUEST", "target": "room"})
            return

        group_id, space_id, name, about_room, nsfw, id = body.group_id, body.space_id, body.creator_id, body.name, body.about_room, body.nsfw, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "room_updated", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "room_updated", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROOMS"]):
            update_status_res = await session.execute(update(Room).where(Room.id == id).values(space_id=space_id, name=name, about_room=about_room, nsfw=nsfw).returning(Room.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("room_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "room_updated", {"index": "UPDATE_FAILED", "target": "room"})
        else:
            await self.__emit_error(sid, id, "room_updated", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROOMS"})
    
    async def __on_edit_message(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "message_edited", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "message_edited", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, EditMessage):
            await self.__emit_error(sid, id, "message_edited", {"index": "WRONG_REQUEST", "target": "message"})
            return

        group_id, room_id, content, id = body.group_id, body.space_id, body.room_id, body.content, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        message_res = await session.execute(select(Message).options(
            selectinload(Message.author),
        ).where(Message.id == id))
        message = message_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "message_edited", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "message_edited", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        if not message:
            await self.__emit_error(sid, id, "message_edited", {"index": "OBJECT_NON_EXISTANT", "target": "message"})
            return
        
        perm_valid = PermissionValidator(client, group)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_MESSAGES"]) or \
        perm_valid.has_room_permissions_all(room_id, ["MANAGE_MESSAGES"]) or \
        message.author.id == client.id:
            update_status_res = await session.execute(update(Message).where(Message.id == id).values(content=content).returning(Message.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("message_edited", {
                    "status": True, 
                    "body": {
                        "content": content,
                        "id": id,
                    }, 
                    "error": None
                }, room=f"#{room_id}")
            else:
                await self.__emit_error(sid, id, "message_edited", {"index": "UPDATE_FAILED", "target": "message"})
        else:
            await self.__emit_error(sid, id, "message_edited", {"index": "MISSING_PERMISSION", "target": "MANAGE_MESSAGES"})

    async def __on_update_role(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "role_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "role_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, UpdateRole):
            await self.__emit_error(sid, id, "role_updated", {"index": "WRONG_REQUEST", "target": "role"})
            return

        group_id, name, color, global_permissions, id = body.group_id, body.name, body.color, body.global_permissions, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "role_updated", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "role_updated", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROLES"]):
            update_status_res = await session.execute(
                update(Role).where(Role.id == id).values(
                    name=name, 
                    color=color, 
                    global_permissions=perm_valid.mask_global_permissions(global_permissions), 
                ).returning(Role.id)
            )
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("role_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "role_updated", {"index": "UPDATE_FAILED", "target": "role"})
        else:
            await self.__emit_error(sid, id, "role_updated", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROLES"})

    async def __on_update_permissions_table(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "permissions_table_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "permissions_table_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, UpdatePermissionsTable):
            await self.__emit_error(sid, id, "permissions_table_updated", {"index": "WRONG_REQUEST", "target": "role"})
            return

        group_id, permissions, id = body.group_id, body.permissions, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "permissions_table_updated", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "permissions_table_updated", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROLES"]):
            update_status_res = await session.execute(
                update(RoleToRoomPerms).where(RoleToRoomPerms.id == id).values(
                    permissions=perm_valid.mask_room_permissions(permissions)
                ).returning(RoleToRoomPerms.id)
            )
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("permissions_table_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "permissions_table_updated", {"index": "UPDATE_FAILED", "target": "permissions_table"})
        else:
            await self.__emit_error(sid, id, "permissions_table_updated", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROLES"})
    
    #ON_DELETE
    async def __on_delete_client(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "client_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "client_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return
         
        deletion_status_res = await session.execute(delete(Client).where(Client.id == client.id))
        deletion_status = deletion_status_res.scalar_one_or_none()
        if deletion_status:
            await self.gateway.emit("client_deleted", {
                "status": True, 
                "body": {"id": client.id}, 
                "error": None
            }, to=sid)
            await self.gateway.disconnect(sid)
        else:
            await self.__emit_error(sid, id, "client_deleted", {"index": "DELETION_FAILED", "target": "client"})
    
    async def __on_delete_group(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "group_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "group_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, DeleteGroup):
            await self.__emit_error(sid, id, "group_deleted", {"index": "WRONG_REQUEST", "target": "group"})
            return

        id = body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.members),
        ).where(Group.id == id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "group_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "group_deleted", {"index": "UNRELATED", "target": "client<->group"})
            return

        if group.owner.id == client.id:
            deletion_status_res = await session.execute(delete(Group).where(Group.id == id).returning(Group.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("group_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${id}")
            else:
                await self.__emit_error(sid, id, "group_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
        else:
            await self.__emit_error(sid, id, "group_deleted", {"index": "DELETION_REJECTED", "target": "group"})

    async def __on_delete_space(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "space_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "space_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, DeleteSpace):
            await self.__emit_error(sid, id, "space_deleted", {"index": "WRONG_REQUEST", "target": "space"})
            return

        group_id, id = body.group_id, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "space_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "space_deleted", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_SPACES"]):
            deletion_status_res = await session.execute(delete(Space).where(Space.id == id).returning(Space.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("space_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "space_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "space"})
        else:
            await self.__emit_error(sid, id, "space_deleted", {"index": "MISSING_PERMISSION", "target": "MANAGE_SPACES"})
    
    async def __on_delete_room(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "room_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "room_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, DeleteRoom):
            await self.__emit_error(sid, id, "room_deleted", {"index": "WRONG_REQUEST", "target": "room"})
            return

        group_id, id = body.group_id, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "room_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "room_deleted", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROOMS"]):
            deletion_status_res = await session.execute(delete(Room).where(Room.id == id).returning(Room.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("room_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "room_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "room"})
        else:
            await self.__emit_error(sid, id, "room_deleted", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROOMS"})
    
    async def __on_delete_message(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "message_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "message_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, DeleteMessage):
            await self.__emit_error(sid, id, "message_deleted", {"index": "WRONG_REQUEST", "target": "message"})
            return

        group_id, room_id, id = body.group_id, body.room_id, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        message_res = await session.execute(select(Message).where(Message.id == id))
        message = message_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "message_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "message_deleted", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        if not message:
            await self.__emit_error(sid, id, "message_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "message"})
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_MESSAGES"]) or \
        perm_valid.has_room_permissions_all(room_id, ["MANAGE_MESSAGES"]) or \
        client.id == message.author_id:
            deletion_status_res = await session.execute(delete(Message).where(Message.id == id).returning(Message.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("message_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${room_id}")
            else:
                await self.__emit_error(sid, id, "message_deleted", {"index": "DELETION_FAILED", "target": "message"})
        else:
            await self.__emit_error(sid, id, "message_deleted", {"index": "MISSING_PERMISSION", "target": "MANAGE_MESSAGES"})
    
    async def __on_delete_role(self, sid, data, session):
        client_session = await self.gateway.get_session(sid)
        client, session_token = client_session["client"], client_session["session_token"]

        if not client:
            await self.__emit_error(sid, client.id, "role_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(session_token):
            await self.__emit_error(sid, client.id, "role_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        body = data.body
        if not isinstance(body, DeleteRole):
            await self.__emit_error(sid, id, "role_deleted", {"index": "WRONG_REQUEST", "target": "role"})
            return

        group_id, id = body.group_id, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, id, "role_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        if not client in group.members:
            await self.__emit_error(sid, id, "role_deleted", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROLES"]):
            deletion_status_res = await session.execute(delete(Role).where(Role.id == id).returning(Role.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("role_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "role_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "role"})
        else:
            await self.__emit_error(sid, id, "role_deleted", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROLES"})


#Add fetchers to router tasks.
    def router_tasks(self):
        @self.router.post("/upload_attachement", response_class=HTMLResponse) #Update code, modify
        async def upload_attachement(request: Request, index: str = Form(...), channel_id: str = Form(...), file: UploadFile = File(...)):
            if request.headers.get('origin') != self.client_server_origin:
                raise HTTPException(status_code=403, detail="Access forbidden.")
            filename = f"{index}.{file.filename.split(".")[-1]}"
            data = await file.read()
            if file.content_type.startswith("image/"):
                save_to = f"{self.storage_images_path}/Images/Attachements/{filename}"
                file_url = f"http://{self.addr[0]}:{self.addr[1]}/images/Attachements/{filename}"
            else:
                save_to = f"{self.storage_files_path}/Files/Attachements{filename}"
                file_url = f"http://{self.addr[0]}:{self.addr[1]}/files/Attachements/{filename}"
            try:
                async with aiofiles.open(save_to, "wb") as buffer:
                    await buffer.write(data)
            except:
                return JSONResponse(content={"success": False}, status_code=201)
            return JSONResponse(content={"url": file_url}, status_code=201)