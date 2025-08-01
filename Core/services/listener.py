from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal
from ..services.worker import event_executer, Client, Group, Space, Room, Message, Role, Permission
from sqlalchemy import insert, select, update, delete
from ast import literal_eval
from datetime import datetime
from ..components import *
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
            ws,  
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
        self.ws = ws
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

        self.gateway.on("create_group", self.__on_create_group)

    async def __on_connect(self, sid, eviron):
        print(f"Client {sid} has connected to the gateway")

    async def __on_disconnect(self, sid):
        print(f"Client {sid} has disconnected from the gateway")
    
    @event_executer #?? may not work here, create extra executer?
    async def __validate_request(self, token: str, session):
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
    
    async def __validate_global_permissions(self, client: Client, group: Group, permission: str):
        if next(role for role in group.roles if client in role.assignees and next(perm for perm in role.permissions if perm.body["global"] and perm.body["permission"] == permission) is not None) is not None:
            return True
        return False

    async def __validate_room_related_permissions(self, client: Client, group: Group, room: Room, permission: str):
        if next(role for role in group.roles if client in role.assignees and next(perm for perm in role.permissions if not perm.body["global"] and perm.body["permission"] == permission and perm.room == room) is not None) is not None:
            return True
        return False

    
    #ON_CREATE_...
    async def __on_create_group(self, sid, data):
        client_id, body = data.client_id, data.body
        name, about_group, icon_url, id = body.name, body.about_group, body.icon_url, body.id
        session.add(Group(owner_id=client_id, name=name, about_group=about_group, icon_url=icon_url, id=id)) 
        await session.commit()
        await self.gateway.emit("group_created", {
            "status": True,
            "body": {
                "id": id
            }
        })

    async def __on_create_space(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, name, id = body.group_id, body.name, body.id
        client = await session.execute(select(Client).where(Client.id == client_id))
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client_id or self.__validate_global_permissions(client, group, "CO_OWNER") or self.__validate_global_permissions(client, group, "MANAGE_SPACES"):
                session.add(Space(group_id=group_id, creator_id=client_id, name=name, id=id)) 
                await session.commit()
                await self.gateway.emit("space_created", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None}, room=f"${group_id}")
            else: await self.gateway.emit("space_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [MANAGE_SPACES] permisions!"}, to=sid)
        else: await self.gateway.emit("space_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"}, to=sid)

    async def __on_create_room(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, space_id, name, about_room, id = body.group_id, body.space_id, body.name, body.about_room, body.id
        client = await session.execute(select(Client).where(Client.id == client_id))
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client_id or self.__validate_global_permissions(client, group, "CO_OWNER") or self.__validate_global_permissions(client, group, "MANAGE_ROOMS"):
                session.add(Room(group_id=group_id, space_id=space_id, creator_id=creator_id, name=name, about_room=about_room, id=id)) 
                await session.commit()
                await self.gateway.emit("room_created", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None}, room=f"${group_id}")
            else: await self.gateway.emit("space_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [MANAGE_ROOMS] permisions!"}, to=sid)
        else: await self.gateway.emit("space_created", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"}, to=sid)

    async def __on_send_message(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, room_id, content, id = data.group_id, data.room_id, data.content, data.id
        client = await session.execute(select(Client).where(Client.id == client_id))
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client_id or self.__validate_global_permissions(client, group, "CO_OWNER") or self.__validate_global_permissions(client, group, "SEND_MESSAGES") or self.__validate_room_related_permissions(group, await session.execute(select(Room).where(Room.id == room_id)), "SEND_MESSAGES"):
                session.add(Message(group_id=group_id, room_id=room_id, author_id=client_id, content=content, id=id)) 
                await session.commit()
                await self.gateway.emit("message_sent", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None}, room=f"#{room_id}")
                await self.gateway.emit("message_sent_notif", {
                    "group_id": group_id,
                    "room_id": room_id, 
                }, room=f"${group_id}")
            else: await self.gateway.emit("message_sent", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Missing [SEND_MESSAGES] permisions!"}, to=sid)
        else: await self.gateway.emit("message_sent", {
                "status": False, 
                "body": {"id": id}, 
                "error": "Object {Group} has no been found!"}, to=sid)
#I've stopped here.
    
    @event_executer
    async def __on_new_role(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, name, id = request.group_id, request.name, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_ROLES"):
                session.add(Role(group_id=group_id, name=name, id=id))
                await session.commit()
                return {
                    "operation": operation_name, 
                    "status": True, 
                    "error": None,
            
                    "body": {
                        "group_id": group_id,
                        "name": name,
                        "id": id,
                    }
                }
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_ROLES] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @event_executer
    async def __on_new_permission(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, role_id, room_id, body, id = request.group_id, request.role_id, request.room_id, request.body, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_ROLES"):
                session.add(Permission(group_id=group_id, role_id=role_id, room_id=room_id, body=body, id=id))
                await session.commit()
                return {
                    "operation": operation_name, 
                    "status": True, 
                    "error": None,
            
                    "body": {
                        "group_id": group_id,
                        "role_id": role_id,
                        "room_id": room_id,
                        "body": body,
                        "id": id,
                    }
                }
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_ROLES] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    

    #ON_UPDATE_...
    @event_executer
    async def __on_update_client(self, sid, data):
        client_id, body = data.client_id, data.body
        nickname, about_me, avatar_url, color_theme = request.nickname, request.about_me, request.avatr_url, request.color_theme
        update_status = await session.execute(update(Client).where(Client.id == client.id).values(nickname=nickname, about_me=about_me, avatar_url=avatar_url, color_theme=color_theme).returning(Client.id))
        if update_status is not None:
            return {
                "operation": operation_name, 
                "status": True, 
                "error": None,
            
                "body": {
                    "nickname": nickname,
                    "about_me": about_me,
                    "avatar_url": avatar_url,
                    "color_theme": color_theme,
                }
            }
        else: return {"operation": operation_name, "status": False, "error": "{Client} object has not been found uhm. what the hell-"}
    
    @event_executer
    async def __on_update_group(self, sid, data):
        client_id, body = data.client_id, data.body
        name, about_group, icon_url, nsfw, content_filter, content_filter_level, id = request.owner_id, request.name, request.about_group, request.icon_url, request.nsfw, request.content_filter, request.content_filter_level, request.id
        group = await session.execute(select(Group).where(Group.id == id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_GROUP"):
                await session.execute(update(Group).where(Group.id == id).values(name=name, about_group=about_group, icon_url=icon_url, nsfw=nsfw, content_filter=content_filter, content_filter_level=content_filter_level))
                return {
                    "operation": operation_name, 
                    "status": True, 
                    "error": None,
            
                    "body": {
                        "name": name,
                        "about_group": about_group,
                        "icon_url": icon_url,
                        "nsfw": nsfw,
                        "id": id,

                        "content_filter": content_filter,
                        "content_filter_level": content_filter_level,
                    }
                }
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_GROUP] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @event_executer
    async def __on_update_space(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, name, id = request.group_id, request.creator_id, request.name, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_SPACES"):
                update_status = await session.execute(update(Space).where(Space.id == id).values(name=name).returning(Space.id))
                if update_status is not None:
                    return {
                        "operation": operation_name, 
                        "status": True, 
                        "error": None,
            
                        "body": {
                            "name": name,
                            "id": id,
                        }
                    }
                else: return {"operation": operation_name, "status": False, "error": "{Space} object has not been found"}
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_SPACES] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @event_executer
    async def __on_update_room(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, space_id, name, about_room, nsfw, id = request.group_id, request.space_id, request.creator_id, request.name, request.about_room, request.nsfw, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_ROOMS"):
                update_status = await session.execute(update(Room).where(Room.id == id).values(space_id=space_id, name=name, about_room=about_room, nsfw=nsfw).returning(Room.id))
                if update_status is not None:
                    return {
                        "operation": operation_name, 
                        "status": True, 
                        "error": None,
            
                        "body": {
                            "name": name,
                            "about_room": about_room,
                            "nsfw": nsfw,
                            "id": id,
                        }
                    }
                else: return {"operation": operation_name, "status": False, "error": "{Room} object has not been found"}
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_ROOMS] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @event_executer
    async def __on_update_message(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, room_id, author_id, content, id = request.group_id, request.space_id, request.room_id, request.author_id, request.content, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or client == await session.execute(select(Client).where(Client.id == author_id)) or self.__validate_global_permissions(group, "MANAGE_MESSAGES") or self.__validate_room_related_permissions(group, await session.execute(select(Room).where(Room.id == room_id)), "MANAGE_MESSAGES"):
                update_status = await session.execute(update(Message).where(Message.id == id).values(content=content).returning(Message.id))
                if update_status is not None:
                    return {
                        "operation": operation_name, 
                        "status": True, 
                        "error": None,
            
                        "body": {
                            "content": content,
                            "id": id,
                        }
                    }
                else: return {"operation": operation_name, "status": False, "error": "{Message} object has not been found"}
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_MESSAGES] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @event_executer
    async def __on_update_role(self, sid, data):
        client_id, body = data.client_id, data.body
        group_id, name, color, id = request.group_id, request.name, request.color, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_ROLES"):
                update_status = await session.execute(update(Role).where(Role.id == id).values(name=name, color=color).returning(Role.id))
                if update_status is not None:
                    return {
                        "operation": operation_name, 
                        "status": True, 
                        "error": None,
            
                        "body": {
                            "name": name,
                            "color": color,
                            "id": id,
                        }
                    }
                else: return {"operation": operation_name, "status": False, "error": "{Role} object has not been found"}
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_ROLES] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}

    
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