from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal
from ..services.worker import Client, Group, Space, Room, Message, Role, Permission
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


class ClientRequest(BaseModel):
    client_id: str
    body: Union[
        UpdateClient, 
        CreateGroup, 
        SendMessage, 
        CreatePermission, 
        CreateRole,
        CreateRoom,
        CreateSpace,
        UpdateGroup,
        UpdateMessage,
        UpdateRole,
        UpdateRoom,
        UpdateSpace,
        DeleteGroup,
        DeleteMessage,
        DeleteRole,
        DeleteRoom,
        DeleteSpace,
        DeletePermission,
    ]

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
        self.router = APIRouter()

        self.event_bindings = {
            "connect": self.__on_connect,
            "disconnect": self.__on_disconnect,

            "create_group": self.__on_create_group,
            "create_space": self.__on_create_space,
            "create_room": self.__on_create_room,
            "send_message": self.__on_send_message,
            "create_role": self.__on_create_role,
            "create_permission": self.__on_create_permission,

            "update_client": self.__on_update_client,
            "update_group": self.__on_update_group,
            "update_space": self.__on_update_space,
            "update_room": self.__on_update_room,
            "edit_message": self.__on_edit_message,
            "update_role": self.__on_update_role,

            "delete_client": self.__on_delete_client,
            "delete_group": self.__on_delete_group,
            "delete_space": self.__on_delete_space,
            "delete_room": self.__on_delete_room,
            "delete_message": self.__on_delete_message,
            "delete_role": self.__on_delete_role,
            "delete_permission": self.__on_delete_permission,
        }
        self.__register_event_handlers()

    def __register_event_handlers(self):
        for event, handler in self.event_bindings.items():
            self.gateway.on(event, self.worker_session(handler))

    async def __emit_error(self, sid, id: int, event: str, error: str):
        await self.gateway.emit(event, {
            "status": False,
            "body": {"id": id},
            "error": error,
        }, to=sid)


    async def __on_connect(self, sid, eviron, auth, session):
        token = auth["session_token"]
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = valid.session_is_valid(token, session)

        if not status:
            raise ConnectionRefusedError("INVALID_OR_EXPIRED_SESSION_TOKEN")
        
        await self.gateway.save_session(sid, {"client": client})

    async def __on_disconnect(self, sid):
        ...

    #ON_CREATE_...
    async def __on_create_group(self, sid, data, session):
        client_id, body = data.client_id, data.body
        name, about_group, icon_url, id = body.name, body.about_group, body.icon_url, body.id

        session.add(Group(owner_id=client_id, name=name, about_group=about_group, icon_url=icon_url, id=id)) 
        await session.commit()

        await self.gateway.emit("group_created", {
            "status": True,
            "body": {"id": id},
            "error": None,
        }, to=sid)

    async def __on_create_space(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, name, id = body.group_id, body.name, body.id

        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.owner),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "space_created", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "space_created", "Object {Group} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)

        if group.owner.id == client_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_SPACES"):

            session.add(Space(group_id=group_id, creator_id=client_id, name=name, id=id)) 
            await session.commit()
            
            await self.gateway.emit("space_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, id, "space_created", "Missing [MANAGE_SPACES] permision!")

    async def __on_create_room(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, space_id, name, about_room, id = body.group_id, body.space_id, body.name, body.about_room, body.id

        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.owner),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "room_created", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "room_created", "Object {Group} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_ROOMS"):
            session.add(Room(group_id=group_id, space_id=space_id, creator_id=client_id, name=name, about_room=about_room, id=id)) 
            await session.commit()

            await self.gateway.emit("room_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, id, "room_created", "Missing [MANAGE_ROOMS] permision!")

    async def __on_send_message(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, room_id, content, id = body.group_id, body.room_id, body.content, body.id

        client_res = await session.execute(select(Client).options(
            selectinload(Client.nickname)
        ).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.owner),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "message_sent", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "message_sent", "Object {Group} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)

        if group.owner.id == client_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("SEND_MESSAGES") or \
        perm_valid.has_room_permission("SEND_MESSAGES", room_id):
            session.add(Message(group_id=group_id, room_id=room_id, author_id=client_id, content=content, id=id)) 
            await session.commit()

            await asyncio.gather(
                self.gateway.emit("message_sent", {
                    "status": True, 
                    "body": {
                        "client_id": client_id,
                        "nickname": client.nickname, 
                        "content": content, 
                        "id": id
                    }, 
                    "error": None
                }, room=f"#{room_id}"),

                self.gateway.emit("message_sent_notif", {
                    "group_id": group_id,
                    "room_id": room_id, 
                }, room=f"${group_id}"),
            )
        else:
            await self.__emit_error(sid, id, "message_sent", "Missing [SEND_MESSAGES] permision!")
    
    async def __on_create_role(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, name, id = body.group_id, body.name, body.id

        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.owner),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "role_created", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "role_created", "Object {Group} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)

        if group.owner.id == client_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_ROLES"):
            session.add(Role(group_id=group_id, name=name, id=id))
            await session.commit()
            await self.gateway.emit("role_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, id, "role_created", "Missing [MANAGE_ROLES] permision!")

    async def __on_create_permission(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, role_id, room_id, body, id = body.group_id, body.role_id, body.room_id, body.body, body.id

        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.owner),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "permission_created", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "permission_created", "Object {Group} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)

        if group.owner.id == client_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_ROLES"):
            session.add(Permission(group_id=group_id, role_id=role_id, room_id=room_id, body=body, id=id))
            await session.commit()
            await self.gateway.emit("permission_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, id, "permission_created", "Missing [MANAGE_ROLES] permision!")
    

    #ON_UPDATE_...
    async def __on_update_client(self, sid, data, session):
        client_id, body = data.client_id, data.body
        nickname, about_me, avatar_url, color_theme = body.nickname, body.about_me, body.avatr_url, body.color_theme

        client_res = await session.execute(select(Client).options(
            selectinload(Client.groups),
        ).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "client_updated", "{Client} unauthorized or non-existant")
            return

        update_status_res = await session.execute(update(Client).where(Client.id == client_id).values(nickname=nickname, about_me=about_me, avatar_url=avatar_url, color_theme=color_theme).returning(Client.id))
        update_status = update_status_res.scalar_one_or_none()
        if update_status:
            emits = [
                self.gateway.emit("client_updated", {
                    "status": True, 
                    "body": {
                        "nickname": nickname, 
                        "avatar_url": avatar_url, 
                        "id": client_id,
                    },
                    "error": None,
                }, room=f"${group.id}")
                for group in client.groups
            ]
            emits.append(
                self.gateway.emit("client_updated", {
                    "status": True, 
                    "body": {"id": client_id},
                    "error": None,
                }, room=sid)
            )
            await asyncio.gather(*emits)
        else:
            await self.__emit_error(sid, id, "client_updated", "Failed to update object {Client}!")

    async def __on_update_group(self, sid, data, session):
        client_id, body = data.client_id, data.body
        name, about_group, icon_url, nsfw, content_filter, content_filter_level, id = body.owner_id, body.name, body.about_group, body.icon_url, body.nsfw, body.content_filter, body.content_filter_level, body.id

        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.owner),
        ).where(Group.id == id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "group_updated", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "group_updated", "Object {Group} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)

        if group.owner.id == client_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_GROUP"):
            update_status_res = await session.execute(update(Group).where(Group.id == id).values(name=name, about_group=about_group, icon_url=icon_url, nsfw=nsfw, content_filter=content_filter, content_filter_level=content_filter_level).returning(Group.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("group_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${id}")
            else:
                await self.__emit_error(sid, id, "group_updated", "Failed to update object {Group}!")
        else:
            await self.__emit_error(sid, id, "group_updated", "Missing [MANAGE_GROUP] permision!")
    
    async def __on_update_space(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, name, id = body.group_id, body.creator_id, body.name, body.id

        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.owner),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "space_updated", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "space_updated", "Object {Group} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)

        if group.owner.id == client_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_SPACES"):
            update_status_res = await session.execute(update(Space).where(Space.id == id).values(name=name).returning(Space.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("space_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "space_updated", "Failed to update object {Space}!")
        else:
            await self.__emit_error(sid, id, "space_updated", "Missing [MANAGE_SPACES] permision!")
    
    async def __on_update_room(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, space_id, name, about_room, nsfw, id = body.group_id, body.space_id, body.creator_id, body.name, body.about_room, body.nsfw, body.id
        
        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.owner),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "room_updated", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "room_updated", "Object {Group} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)

        if group.owner.id == client_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_ROOMS"):
            update_status_res = await session.execute(update(Room).where(Room.id == id).values(space_id=space_id, name=name, about_room=about_room, nsfw=nsfw).returning(Room.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("room_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "room_updated", "Failed to update object {Room}!")
        else:
            await self.__emit_error(sid, id, "room_updated", "Missing [MANAGE_ROOMS] permision!")
    
    async def __on_edit_message(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, room_id, content, id = body.group_id, body.space_id, body.room_id, body.content, body.id
        
        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.owner),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        message_res = await session.execute(select(Message).options(
            selectinload(Message.author),
        ).where(Message.id == id))
        message = message_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "message_edited", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "message_edited", "Object {Group} has not been found!")
            return
        
        if not message:
            await self.__emit_error(sid, id, "message_edited", "Object {Message} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)

        if group.owner.id == client_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_MESSAGES") or \
        perm_valid.has_room_permission("MANAGE_MESSAGES", room_id) or \
        message.author.id == client_id:
            update_status_res = await session.execute(update(Message).where(Message.id == id).values(content=content).returning(Message.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("message_edited", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"#{room_id}")
            else:
                await self.__emit_error(sid, id, "message_edited", "Failed to update object {Message}!")
        else:
            await self.__emit_error(sid, id, "message_edited", "Missing [MANAGE_MESSAGES] permision!")

    async def __on_update_role(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, name, color, id = body.group_id, body.name, body.color, body.id

        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.owner),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "role_updated", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "role_updated", "Object {Group} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_ROLES"):
            update_status_res = await session.execute(update(Role).where(Role.id == id).values(name=name, color=color).returning(Role.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("role_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "role_updated", "Failed to update object {Role}!")
        else:
            await self.__emit_error(sid, id, "role_updated", "Missing [MANAGE_ROLES] permision!")
    
    #ON_DELETE
    async def __on_delete_client(self, sid, data, session):
        client_id, _ = data.client_id, data.body
        
        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, client_id, "client_deleted", "{Client} unauthorized or non-existant")
            return
         
        await session.execute(delete(Client).where(Client.id == client_id))
        await self.gateway.emit("client_deleted", {
            "status": True, 
            "body": {"id": client_id}, 
            "error": None
        }, to=sid)
    
    async def __on_delete_group(self, sid, data, session):
        client_id, body = data.client_id, data.body
        id = body.id

        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).where(Group.id == id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "group_deleted", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "group_deleted", "Object {Group} has not been found!")
            return

        if group.owner.id == client.id:
            deletion_status_res = await session.execute(delete(Group).where(Group.id == id).returning(Group.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("client_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${id}")
            else:
                await self.__emit_error(sid, id, "group_deleted", "Object {Group} has not been found!")
        else:
            await self.__emit_error(sid, id, "group_deleted", "Operation has been rejected")

    async def __on_delete_space(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, id = body.group_id, body.id
        
        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "group_deleted", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "group_deleted", "Object {Group} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)

        if group.owner.id == client.id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_SPACES"):
            deletion_status_res = await session.execute(delete(Space).where(Space.id == id).returning(Space.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("space_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "space_deleted", "Object {Space} has not been found!")
        else:
            await self.__emit_error(sid, id, "space_deleted", "Missing [MANAGE_SPACES] permision!")
    
    async def __on_delete_room(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, id = body.group_id, body.id

        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "room_deleted", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "room_deleted", "Object {Group} has not been found!")
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_ROOMS"):
            deletion_status_res = await session.execute(delete(Room).where(Room.id == id).returning(Room.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("room_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "room_deleted", "Object {Room} has not been found!")
        else:
            await self.__emit_error(sid, id, "room_deleted", "Missing [MANAGE_ROOMS] permision!")
    
    async def __on_delete_message(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, room_id, id = body.group_id, body.room_id, body.id
       
        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        message_res = await session.execute(select(Message).where(Message.id == id))
        message = message_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "message_deleted", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "message_deleted", "Object {Group} has no been found!")
            return
        
        if not message:
            await self.__emit_error(sid, id, "message_deleted", "Object {Message} has no been found!")
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client_id or \
        client_id == message.author_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_MESSAGES") or \
        perm_valid.has_room_permission("MANAGE_MESSAGES", room_id):
            deletion_status_res = await session.execute(delete(Message).where(Message.id == id).returning(Message.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("message_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${room_id}")
            else:
                await self.__emit_error(sid, id, "message_deleted", "Failed to delete object {Message}")
        else:
            await self.__emit_error(sid, id, "message_deleted", "Missing [MANAGE_MESSAGES] permision!")
    
    async def __on_delete_role(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, id = body.group_id, body.id

        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "role_deleted", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "role_deleted", "Object {Group} has no been found!")
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_ROLES"):
            deletion_status_res = await session.execute(delete(Role).where(Role.id == id).returning(Role.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("role_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "role_deleted", "Object {Role} has no been found!")
        else:
            await self.__emit_error(sid, id, "role_deleted", "Missing [MANAGE_ROLES] permision!")

    async def __on_delete_permission(self, sid, data, session):
        client_id, body = data.client_id, data.body
        group_id, id = body.group_id, body.id
        
        client_res = await session.execute(select(Client).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not client:
            await self.__emit_error(sid, id, "permission_deleted", "{Client} unauthorized or non-existant")
            return

        if not group:
            await self.__emit_error(sid, id, "permission_deleted", "Object {Group} has no been found!")
            return
        
        perm_valid = PermissionValidator(client, group)
        
        if group.owner.id == client.id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permission("MANAGE_ROLES"):
            deletion_status_res = await session.execute(delete(Permission).where(Permission.id == id).returning(Permission.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status is not None:
                await self.gateway.emit("permission_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, id, "permission_deleted", "Object {Permission} has no been found!")
        else:
            await self.__emit_error(sid, id, "permission_deleted", "Missing [MANAGE_ROLES] permision!")
#I've stopped here.
#To remove tomorrow: >

    #LISTENER
    def router_tasks(self):
        @self.router.websocket("/gateway")
        async def listener(websocket: WebSocket, token: str = Depends(self.oauth2)):
            await websocket.accept()
            status, client = await self.__validate_request(token, self.ws)
            if status:
                try:
                    while True:
                        data = await websocket.receive_json()
                        await self.__total_interpreter(data, client, websocket)
                except WebSocketDisconnect:
                    await websocket.close()
            else:
                await websocket.send_json({"connection_status": False, "error": "invalid or outdated session"})
                await websocket.close()

        @self.router.websocket("/heartbeat")
        async def listener(websocket: WebSocket, token: str = Depends(self.oauth2)):
            await websocket.accept()
            status, _ = await self.__validate_request(token, self.ws)
            if status:
                try:
                    while True:
                        await websocket.send_json({
                            "status": True,
                            "error": None,
                            "interval": self.heartbeat_interval,
                        })
                        try:
                            data = HeartbeatRequest(await asyncio.wait_for(websocket.receive_json(), (self.heartbeat_interval // 1000) // 2)) #Server waiting time is two times less than the original interval
                            if self.__validate_heartbeat_request(data):
                                await asyncio.sleep(self.heartbeat_interval // 1000)
                            else:
                                await websocket.send_json({"connection_status": False, "error": "Unusual client behaviour, connection closed automatically"})
                                await websocket.close()
                        except asyncio.TimeoutError:
                            await websocket.send_json({"connection_status": False, "error": "Client skipped heartbeat, connection closed automatically"})
                            await websocket.close()
                except WebSocketDisconnect:
                    await websocket.close()
            else:
                await websocket.send_json({"connection_status": False, "error": "Invalid or outdated session!"})
                await websocket.close()
        
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