from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal
from ..services.worker import executer, Client, Group, Space, Room, Message, Role, Permission
from sqlalchemy import insert, select, update, delete
from ast import literal_eval
from datetime import datetime
from ..components import *
from PIL import Image
import aiofiles
import asyncio
import json
import time
import jwt
import io
import os


class HeartbeatRequest(BaseModel):
    type: Literal['receive_heartbeat']
    status: bool
    error: Union[str, None]

ClientRequest = Annotated[Union[
    UpdateClient, 
    NewGroup, 
    NewMessage, 
    NewPermission, 
    NewRole,
    NewRoom,
    NewSpace,
    UpdateGroup,
    UpdateMessage,
    UpdateRole,
    UpdateRoom,
    UpdateSpace,
    DeleteClient,
    DeleteGroup,
    DeleteMessage,
    DeleteRole,
    DeleteRoom,
    DeleteSpace,
    DeletePermission,
    ], _type(discriminator='type')]

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
        self.router = APIRouter()

        self.types = { 
            "new_group": {"ref": NewGroup, "func": self.__on_new_group, "name": "on_new_group"},
            "new_message": {"ref": NewMessage, "func": self.__on_new_message, "name": "on_new_message"},
            "new_permission": {"ref": NewPermission, "func": self.__on_new_permission, "name": "on_new_permission"},
            "new_role": {"ref": NewRole, "func": self.__on_new_role, "name": "on_new_role"},
            "new_room": {"ref": NewRoom, "func": self.__on_new_room, "name": "on_new_room"},
            "new_space": {"ref": NewSpace, "func": self.__on_new_space, "name": "on_new_space"},

            "update_client": {"ref": UpdateClient, "func": self.__on_update_client, "name": "on_update_client"},
            "update_group": {"ref": NewGroup, "func": self.__on_update_group, "name": "on_update_group"},
            "update_message": {"ref": NewMessage, "func": self.__on_update_message, "name": "on_update_message"},
            "update_role": {"ref": NewRole, "func": self.__on_update_role, "name": "on_update_role"},
            "update_room": {"ref": NewRoom, "func": self.__on_update_room, "name": "on_update_room"},
            "update_space": {"ref": NewSpace, "func": self.__on_update_space, "name": "on_update_space"},

            "delete_client": {"ref": DeleteClient, "func": self.__on_delete_client, "name": "on_delete_client"},
            "delete_group": {"ref": DeleteGroup, "func": self.__on_delete_group, "name": "on_delete_group"},
            "delete_message": {"ref": DeleteMessage, "func": self.__on_delete_message, "name": "on_delete_message"},
            "delete_role": {"ref": DeleteRole, "func": self.__on_delete_role, "name": "on_delete_role"},
            "delete_room": {"ref": DeleteRoom, "func": self.__on_delete_room, "name": "on_delete_room"},
            "delete_space": {"ref": DeleteSpace, "func": self.__on_delete_space, "name": "on_delete_space"},
            "delete_permission": {"ref": DeletePermission, "func": self.__on_delete_permission, "name": "on_delete_permission"},
        }
    
    @executer
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
    
    async def __validate_global_permissions(self, group: Group, permission: str):
        if next(role for role in group.roles if next(perm for perm in role.permissions if perm.body["global"] and perm.body["permission"] == permission) is not None) is not None:
            return True
        return False

    async def __validate_room_related_permissions(self, group: Group, room: Room, permission: str):
        if next(role for role in group.roles if next(perm for perm in role.permissions if not perm.body["global"] and perm.body["permission"] == permission and perm.room == room) is not None) is not None:
            return True
        return False
    
    def __validate_heartbeat_request(self, request: object):
        if (not request.status and not request.error) or (request.status and request.error):
            return False
        return True

    async def __total_interpreter(self, data: dict, client: Client, socket: WebSocket):
        adapter = TypeAdapter(ClientRequest)
        request = adapter.validate_python(data)
        if request.type in self.types:
            if isinstance(request, self.types[request.type]["ref"]):
                func = self.types[request.type]["func"]
                response = await func(request, client, self.types[request.type]["name"], self.ws)
                if response is not None:
                    if isinstance(response, tuple):
                        for instance in response: #In case if double, triple, etc (like... really rare, chill)
                            await socket.send_json(instance)
                    else: await socket.send_json(response)
    
    #ON_NEW_...
    @executer
    async def __on_new_group(self, request, client: Client, operation_name: str, session):
        owner_id, name, about_group, icon_url, id = request.owner_id, request.name, request.about_group, request.icon_url, request.id
        session.add(Group(owner_id=owner_id, name=name, about_group=about_group, icon_url=icon_url, id=id)) 
        await session.commit()
        return {
            "operation": operation_name, 
            "status": True, 
            "error": None,
            
            "body": {
                "owner_id": owner_id,
                "name": name,
                "about_group": about_group,
                "icon_url": icon_url,
                "id": id,
            }
        }
    
    @executer
    async def __on_new_space(self, request, client: Client, operation_name: str, session):
        group_id, creator_id, name, id = request.group_id, request.creator_id, request.name, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_SPACES"):
                session.add(Space(group_id=group_id, creator_id=creator_id, name=name, id=id)) 
                await session.commit()
                return {
                    "operation": operation_name, 
                    "status": True, 
                    "error": None,
            
                    "body": {
                        "group_id": group_id,
                        "creator_id": creator_id,
                        "name": name,
                        "id": id,
                    }
                }
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_SPACES] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @executer
    async def __on_new_room(self, request, client: Client, operation_name: str, session):
        group_id, space_id, creator_id, name, about_room, id = request.group_id, request.space_id, request.creator_id, request.name, request.about_room, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "MANAGE_ROOMS"):
                session.add(Room(group_id=group_id, space_id=space_id, creator_id=creator_id, name=name, about_room=about_room, id=id)) 
                await session.commit()
                return {
                    "operation": operation_name, 
                    "status": True, 
                    "error": None,
            
                    "body": {
                        "group_id": group_id,
                        "space_id": space_id,
                        "creator_id": creator_id,
                        "name": name,
                        "about_room": about_room,
                        "id": id,
                    }
                }
            else: return {"operation": operation_name, "status": False, "error": "Missing [MANAGE_ROOMS] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @executer
    async def __on_new_message(self, request, client: Client, operation_name: str, session):
        group_id, space_id, room_id, author_id, content, id = request.group_id, request.space_id, request.room_id, request.author_id, request.content, request.id
        group = await session.execute(select(Group).where(Group.id == group_id))
        if group is not None:
            if group.owner.id == client.id or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_global_permissions(group, "SEND_MESSAGES") or self.__validate_room_related_permissions(group, await session.execute(select(Room).where(Room.id == room_id)), "SEND_MESSAGES"):
                session.add(Message(group_id=group_id, space_id=space_id, room_id=room_id, author_id=author_id, content=content, id=id)) 
                await session.commit()
                return {
                    "operation": operation_name, 
                    "status": True, 
                    "error": None,
            
                    "body": {
                        "group_id": group_id,
                        "space_id": space_id,
                        "room_id": room_id,
                        "author_id": author_id,
                        "content": content,
                        "id": id,
                    }
                }
            else: return {"operation": operation_name, "status": False, "error": "Missing [SEND_MESSAGES] permissions!"}
        else: return {"operation": operation_name, "status": False, "error": "{Group} object has not been found"}
    
    @executer
    async def __on_new_role(self, request, client: Client, operation_name: str, session):
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
    
    @executer
    async def __on_new_permission(self, request, client: Client, operation_name: str, session):
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
    @executer
    async def __on_update_client(self, request, client: Client, operation_name: str, session):
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
    
    @executer
    async def __on_update_group(self, request, client: Client, operation_name: str, session):
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
    
    @executer
    async def __on_update_space(self, request, client: Client, operation_name: str, session):
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
    
    @executer
    async def __on_update_room(self, request, client: Client, operation_name: str, session):
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
    
    @executer
    async def __on_update_message(self, request, client: Client, operation_name: str, session):
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
    
    @executer
    async def __on_update_role(self, request, client: Client, operation_name: str, session):
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
    @executer
    async def __on_delete_client(self, request, client: Client, operation_name: str, session):
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
    
    @executer
    async def __on_delete_group(self, request, client: Client, operation_name: str, session):
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
    
    @executer
    async def __on_delete_space(self, request, client: Client, operation_name: str, session):
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
    
    @executer
    async def __on_delete_room(self, request, client: Client, operation_name: str, session):
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
    
    @executer
    async def __on_delete_message(self, request, client: Client, operation_name: str, session):
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
    
    @executer
    async def __on_delete_role(self, request, client: Client, operation_name: str, session):
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

    @executer
    async def __on_delete_permission(self, request, client: Client, operation_name: str, session):
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