from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal
from ..services.worker import worker_session, Client, Group, Space, Room, Message, Role, Permission
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
        }
        self.__register_event_handlers()

    def __register_event_handlers(self):
        for event, handler in self.event_bindings.items():
            self.gateway.on(event, self.worker_session(handler))

    async def __on_connect(self, sid, eviron):
        print(f"Client {sid} has connected to the gateway")

    async def __on_disconnect(self, sid):
        print(f"Client {sid} has disconnected from the gateway")
    
    async def __validate_request(self, token: str, session): #? Might change later
        payload = jwt.decode(token, self.access_key, algorithm=self.algorithm)
        username, id = payload["username"], payload["id"]
        client = session.execute(select(Client).where(
            Client.username == username, 
            Client.id == id, 
            Client.token == token))
        if client is not None:
            if datetime.now(datetime.timezone.utc) > client.token_expires_at:
                return False, None
            return True, client
        return False, None


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
            await self.gateway.emit("space_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "{Client} unauthorized or non-existant"
            }, to=sid)
            return

        if not group:
            await self.gateway.emit("space_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"
            }, to=sid)
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
            await self.gateway.emit("space_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [MANAGE_SPACES] permisions!"
            }, to=sid)

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
            await self.gateway.emit("room_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "{Client} unauthorized or non-existant"
            }, to=sid)
            return

        if not group:
            await self.gateway.emit("room_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"
            }, to=sid)
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
            await self.gateway.emit("room_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [MANAGE_ROOMS] permisions!"
            }, to=sid)

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
            await self.gateway.emit("message_sent", {
                "status": False, 
                "body": {"id": id}, 
                "error": "{Client} unauthorized or non-existant"
            }, to=sid)
            return

        if not group:
            await self.gateway.emit("message_sent", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"
            }, to=sid)
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
            await self.gateway.emit("message_sent", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [SEND_MESSAGES] permisions!"
            }, to=sid)
    
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
            await self.gateway.emit("role_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "{Client} unauthorized or non-existant"
            }, to=sid)
            return

        if not group:
            await self.gateway.emit("role_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"
            }, to=sid)
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
            await self.gateway.emit("role_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [MANAGE_ROLES] permisions!"
            }, to=sid)

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
            await self.gateway.emit("permission_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "{Client} unauthorized or non-existant"
            }, to=sid)
            return

        if not group:
            await self.gateway.emit("permision_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"
            }, to=sid)
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
            await self.gateway.emit("permission_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [MANAGE_ROLES] permisions!"
            }, to=sid)
    

    #ON_UPDATE_...
    async def __on_update_client(self, sid, data, session):
        client_id, body = data.client_id, data.body
        nickname, about_me, avatar_url, color_theme = body.nickname, body.about_me, body.avatr_url, body.color_theme

        client_res = await session.execute(select(Client).options(
            selectinload(Client.groups),
        ).where(Client.id == client_id))
        client = client_res.scalar_one_or_none()

        if not client:
            await self.gateway.emit("client_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "{Client} unauthorized or non-existant"
            }, to=sid)
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
            await self.gateway.emit("client_updated", {
                "status": False, 
                "body": {"id": client_id}, 
                "error": "Object {Client} has no been found, why?!"
            }, to=sid)

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
            await self.gateway.emit("group_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "{Client} unauthorized or non-existant"
            }, to=sid)
            return

        if not group:
            await self.gateway.emit("group_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"
            }, to=sid)
            return
        
        perm_valid = PermissionValidator(client, group)

        if group.owner.id == client_id or \
        perm_valid.has_global_permission("CO_OWNER") or \
        perm_valid.has_global_permissions("MANAGE_GROUP"):
            await session.execute(update(Group).where(Group.id == id).values(name=name, about_group=about_group, icon_url=icon_url, nsfw=nsfw, content_filter=content_filter, content_filter_level=content_filter_level))
            await self.gateway.emit("group_updated", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${id}")

        else:
            await self.gateway.emit("group_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [MANAGE_GROUP] permisions!"
            }, to=sid)
    
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
            await self.gateway.emit("space_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "{Client} unauthorized or non-existant"
            }, to=sid)
            return

        if not group:
            await self.gateway.emit("space_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"
            }, to=sid)
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
                await self.gateway.emit("space_updated", {
                    "status": False, 
                    "body": {"id": id}, 
                    "error": "Object {Space} has no been found!"
                }, to=sid)
        
        else:
            await self.gateway.emit("space_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [MANAGE_SPACES] permisions!"
            }, to=sid)
    
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
            await self.gateway.emit("room_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "{Client} unauthorized or non-existant"
            }, to=sid)
            return

        if not group:
            await self.gateway.emit("room_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"
            }, to=sid)
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
                await self.gateway.emit("room_updated", {
                    "status": False, 
                    "body": {"id": id}, 
                    "error": "Object {Room} has no been found!"
                }, to=sid)
        
        else:
            await self.gateway.emit("room_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [MANAGE_ROOMS] permisions!"
            }, to=sid)
    
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
            await self.gateway.emit("message_edited", {
                "status": False, 
                "body": {"id": id}, 
                "error": "{Client} unauthorized or non-existant"
            }, to=sid)
            return

        if not group:
            await self.gateway.emit("message_edited", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"
            }, to=sid)
            return
        
        if not message:
            await self.gateway.emit("message_edited", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Message} has no been found!"
            }, to=sid)
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
                await self.gateway.emit("message_edited", {
                    "status": False, 
                    "body": {"id": id}, 
                    "error": "Object {Message} has no been found!"
                }, to=sid)
        else:
            await self.gateway.emit("message_edited", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [MANAGE_MESSAGES] permisions!"
            }, to=sid)

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
            await self.gateway.emit("role_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "{Client} unauthorized or non-existant"
            }, to=sid)
            return

        if not group:
            await self.gateway.emit("role_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"
            }, to=sid)
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
                await self.gateway.emit("role_updated", {
                    "status": False, 
                    "body": {"id": id}, 
                    "error": "Object {Role} has no been found!"
                }, to=sid)
        else:
            await self.gateway.emit("role_updated", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [MANAGE_ROLES] permisions!"
            }, to=sid)
#I've stopped here.
    
    #ON_DELETE
    @event_executer
    async def __on_delete_client(self, sid, data):
        client_id, body = data.client_id, data.body
        id = request.id
        if id == client.id:
            deletion_status = await session.execute(delete(Client).where(Client.id == id).returning(Client.id))
            if deletion_status is not None:
                return {
                        "operation": operation_name, 
                        "status": True, 
                        "error": None,
            
                        "body": {
                            "id": id,
                        }
                    }
            else: return {"operation": operation_name, "status": False, "error": "{Client} object has not been found"}
        else: return {"operation": operation_name, "status": False, "error": "Operation prohibited"}
    
    @event_executer
    async def __on_delete_group(self, sid, data):
        client_id, body = data.client_id, data.body
        owner_id, id = request.owner_id, request.id
        group = await session.execute(select(Group).where(Group.id == id))
        if group is not None:
            if group.owner.id == client.id:
                deletion_status = await session.execute(delete(Group).where(Group.id == id).returning(Group.id))
                if deletion_status is not None:
                    return {
                        "operation": operation_name, 
                        "status": True, 
                        "error": None,
            
                        "body": {
                            "owner_id": owner_id,
                            "id": id,
                        }
                    }
                else: return {"operation": operation_name, "status": False, "error": "{Group} object refuses to be deleted!"}
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_GROUP] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @event_executer
    async def __on_delete_space(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, id = request.group_id, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_SPACES"):
                deletion_status = await session.execute(delete(Space).where(Space.id == id).returning(Space.id))
                if deletion_status is not None:
                    return {
                        "operation": operation_name, 
                        "status": True, 
                        "error": None,
            
                        "body": {
                            "id": id,
                        }
                    }
                else: return {"operation": operation_name, "status": False, "error": "{Space} object has not been found"}
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_SPACES] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @event_executer
    async def __on_delete_room(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, id = request.group_id, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_ROOMS"):
                deletion_status = await session.execute(delete(Room).where(Room.id == id).returning(Room.id))
                if deletion_status is not None:
                    return {
                        "operation": operation_name, 
                        "status": True, 
                        "error": None,
            
                        "body": {
                            "id": id,
                        }
                    }
                else: return {"operation": operation_name, "status": False, "error": "{Room} object has not been found"}
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_ROOMS] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @event_executer
    async def __on_delete_message(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, room_id, author_id, id = request.group_id, request.room_id, request.author_id, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or client == await session.execute(select(Client).where(Client.id == author_id)) or self.__validate_global_permissions(group, "MANAGE_MESSAGES") or self.__validate_room_related_permissions(group, await session.execute(select(Room).where(Room.id == room_id)), "MANAGE_MESSAGES"):
                deletion_status = await session.execute(delete(Message).where(Message.id == id).returning(Message.id))
                if deletion_status is not None:
                    return {
                        "operation": operation_name, 
                        "status": True, 
                        "error": None,
            
                        "body": {
                            "id": id,
                        }
                    }
                else: return {"operation": operation_name, "status": False, "error": "{Message} object has not been found"}
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_MESSAGES] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @event_executer
    async def __on_delete_role(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, id = request.group_id, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_ROLES"):
                deletion_status = await session.execute(delete(Role).where(Role.id == id).returning(Role.id))
                if deletion_status is not None:
                    return {
                        "operation": operation_name, 
                        "status": True, 
                        "error": None,
            
                        "body": {
                            "id": id,
                        }
                    }
                else: return {"operation": operation_name, "status": False, "error": "{Role} object has not been found"}
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_ROLES] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}

    @event_executer
    async def __on_delete_permission(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, id = request.group_id, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_ROLES"):
                deletion_status = await session.execute(delete(Permission).where(Permission.id == id).returning(Permission.id))
                if deletion_status is not None:
                    return {
                        "operation": operation_name, 
                        "status": True, 
                        "error": None,
            
                        "body": {
                            "id": id,
                        }
                    }
                else: return {"operation": operation_name, "status": False, "error": "{Permission} object has not been found"}
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_ROLES] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}

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