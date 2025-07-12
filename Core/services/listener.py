from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from ..components.client import UpdateClient
from ..components.group import NewGroup, UpdateGroup
from ..components.message import NewMessage, UpdateMessage
from ..components.permission import NewPermission, DeletePermission
from ..components.role import NewRole, UpdateRole
from ..components.room import NewRoom, UpdateRoom
from ..components.space import NewSpace, UpdateSpace
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal
from worker import executer, Client, Group, Space, Room, Message, Role, Permission
from sqlalchemy import insert, select, update, delete
from ast import literal_eval
from datetime import datetime
from PIL import Image
import aiofiles
import json
import jwt
import io
import os


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
            "update_message": {"ref": NewMessage, "func": ..., "name": "on_update_message"},
            "update_role": {"ref": NewRole, "func": ..., "name": "on_update_role"},
            "update_room": {"ref": NewRoom, "func": ..., "name": "on_update_room"},
            "update_space": {"ref": NewSpace, "func": ..., "name": "on_update_space"},

            "delete_permission": {"ref": NewPermission, "func": ..., "name": "on_new_permission"},
        }
    
    @executer
    async def __validate_request(self, token: str, session):
        payload = jwt.decode(token, self.access_key, algorithm=self.algorithm)
        username, id = payload["username"], payload["id"]
        client = session.execute(select(Client).where(Client.username == username, Client.id == id, Client.token == token))
        if client: return True, client
        return False, None
    
    async def __validate_global_permissions(self, group: Group, permission: str):
        if next(role for role in group.roles if next(perm for perm in role.permissions if perm.body["global"] and perm.body["permission"] == permission) is not None) is not None:
            return True
        return False

    async def __validate_room_related_permissions(self, group: Group, permission: str):
        if next(role for role in group.roles if next(perm for perm in role.permissions if not perm.body["global"] and perm.body["permission"] == permission) is not None) is not None:
            return True
        return False

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
    
    @executer
    async def __on_new_room(self, request, client: Client, operation_name: str, session):
        group_id, space_id, creator_id, name, about_room, id = request.group_id, request.space_id, request.creator_id, request.name, request.about_room, request.id
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
    
    @executer
    async def __on_new_message(self, request, client: Client, operation_name: str, session):
        group_id, space_id, room_id, author_id, content, id = request.group_id, request.space_id, request.room_id, request.author_id, request.content, request.id
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
    
    @executer
    async def __on_new_role(self, request, client: Client, operation_name: str, session):
        group_id, name, id = request.group_id, request.name, request.id
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
    
    @executer
    async def __on_new_permission(self, request, client: Client, operation_name: str, session):
        group_id, role_id, room_id, body, id = request.group_id, request.role_id, request.room_id, request.body, request.id
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
    

    #ON_UPDATE_...
    @executer
    async def __on_update_client(self, request, client: Client, operation_name: str, session):
        nickname, about_me, avatar_url, color_theme, id = request.nickname, request.about_me, request.avatr_url, request.color_theme, request.id
        await session.execute(update(Client).where(Client.id == id).values(nickname=nickname, about_me=about_me, avatar_url=avatar_url, color_theme=color_theme))
        return {
            "operation": operation_name, 
            "status": True, 
            "error": None,
            
            "body": {
                "nickname": nickname,
                "about_me": about_me,
                "avatar_url": avatar_url,
                "color_theme": color_theme,
                "id": id,
            }
        }
    
    @executer
    async def __on_update_group(self, request, client: Client, operation_name: str, session):
        owner_id, name, about_group, icon_url, nsfw, content_filter, content_filter_level, id = request.owner_id, request.name, request.about_group, request.icon_url, request.nsfw, request.content_filter, request.content_filter_level, request.id
        group = await session.execute(select(Group).where(Group.id == id))
        if group is not None:
            if group.owner == client or self.__validate_global_permissions(group, "CO_OWNER") or self.__validate_room_related_permissions(group, "MANAGE_GROUP"):
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
        else: return {"operation": operation_name, "status": False, "error": "Group object has not been found"}
    
    @executer
    async def __on_update_space(self, request, client: Client, operation_name: str, session):
        group_id, creator_id, name, id = request.group_id, request.creator_id, request.name, request.id
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
    
    @executer
    async def __on_update_room(self, request, client: Client, operation_name: str, session):
        group_id, space_id, creator_id, name, about_room, id = request.group_id, request.space_id, request.creator_id, request.name, request.about_room, request.id
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
    
    @executer
    async def __on_update_message(self, request, client: Client, operation_name: str, session):
        group_id, space_id, room_id, author_id, content, id = request.group_id, request.space_id, request.room_id, request.author_id, request.content, request.id
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
    
    @executer
    async def __on_update_role(self, request, client: Client, operation_name: str, session):
        group_id, name, id = request.group_id, request.name, request.id
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



    async def __on_modal(self, request, client_id: int):
        response = await self.__modal_interpreter(request, client_id)
        return response

    async def __on_group(self, request, client_id: int):
        id, image_select_path, name, desc = request.id, request.image_select_path, next(_ for _ in request.fields if _.index == "name").input, next(_ for _ in request.fields if _.index == "desc").input
        status, preset_id, preset_name = await self.dmp.create_group(name, client_id, id // 200, image_select_path, desc) # // for test only!
        if status: return ({
            "type": "group",
            "id": id // 200, # // for test only!
            "owner_id": client_id,
            "icon_path": image_select_path,
            "name": name,
            "desc": desc,
        },
        {
            "type": "self_create_channel",
            "id": preset_id,
            "creator_id": client_id,
            "group_id": id // 200, # // for test only!
            "name": preset_name,
        },
        {"type": "modal_status", "status": True, "error": None},)
        else: return {"type": "modal_status", "status": False, "error": "Can't create group"}
    
    async def __on_channel(self, request, client_id: int):
        id, group_id, name = request.id, next(_ for _ in request.fields if _.index == "group_id").input, next(_ for _ in request.fields if _.index == "name").input
        group = await self.dmp.fetch_group_by_id(group_id)
        if group != False and group is not None:
            status = await self.dmp.create_channel(client_id, name, id // 200, group_id) # // for test only!
            if status:
                request =  {
                    "type": "channel",
                    "id": id // 200, # // for test only!
                    "creator_id": client_id,
                    "group_id": group_id,
                    "name": name,
                }
                await self.cmp.broadcast(request, group.members)
                request["type"] = 'self_create_channel'
                return (request, {"type": "modal_status", "status": True, "error": None})
            else: return {"type": "modal_status", "status": False, "error": "Can't create channel"}

    async def __on_message(self, request, client_id: int):
        id, sender_id, group_id, channel_id, sender_name, sender_icon_path, content = request.id, request.sender_id, request.group_id, request.channel_id, request.sender_name, request.sender_icon_path, request.content
        group = await self.dmp.fetch_group_by_id(group_id)
        if group != False and group is not None:
            status = await self.dmp.save_message(sender_id, group_id, channel_id, content, id)
            if status: 
                request = {
                    "type": "message",
                    "id": id,
                    "sender_id": sender_name,
                    "group_id": group_id,
                    "channel_id": channel_id,
                    "sender_name": sender_name,
                    "sender_icon_path": sender_icon_path,
                    "content": content,
                    "unred": True,
                }
                await self.cmp.broadcast(request, group.members)
                return (request, {"type": "message_creation_status", "status": True, "error": None})
            else: return {"type": "message_creation_status", "status": False, "error": "Can't send message."}

    async def __on_friend_request(self, request, client_id: int):
        id, username = request.id, next(_ for _ in request.fields if _.index == "username").input
        client = await self.dmp.fetch_client_by_id(client_id)
        co_client = await self.dmp.fetch_client_by_username(username)
        if co_client != False:
            if co_client is not None:
                request = {
                    "type": "friend_request",
                    "id": id,
                    "client_id": client_id,
                    "client_name": client.name,
                }
                status = await self.cmp.notify(request, co_client.id, self.dmp)
                if not status:
                    return {"type": "modal_status", "status": False, "error": "Can't friend user."}
                return (request, {"type": "modal_status", "status": True, "error": None})
            else: return {"type": "modal_status", "status": False, "error": "User with such username does not exist!"}
        else: return {"type": "modal_status", "status": False, "error": "Error occured while trying to fetch user with that username."}

    async def __on_group_request_members(self, request, client_id: int):
        id = request.id
        group = await self.dmp.fetch_group_by_id(id)
        if group != False and group is not None:
            members = []
            for member in group.members:
                members.append({
                    "type": "member", 
                    "id": member.id, 
                    "name": member.diplay_name, 
                    "icon_path": member.icon_path, 
                    "status": await self.cmp.fetch_status(member.id),
                    })
            request = {
                "type": "group_load_members",
                "id": id,
                "members": members,
            }
            return request

    def router_tasks(self):
        @self.router.websocket("/listener")
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
                await websocket.send_json({"connection_status": False, "error": "invalid or outdated access token"})
                await websocket.close()

        @self.router.post("/validate", response_class=HTMLResponse)
        async def validate(request: Request, creds: GrabCreds):
            if request.headers.get('origin') != self.client_server_origin:
                raise HTTPException(status_code=403, detail="Access forbidden.")

            if creds.token is None:
                raise HTTPException(status_code=400)
            try:
                payload = jwt.decode(creds.token, self.access_key, algorithms=[self.algorithm])
                username = payload["username"]
                id = payload["id"]
                if username is None or id is None or id != creds.id:
                    raise HTTPException(status_code=400)
            except:
                raise HTTPException(status_code=400)
            client = await self.dmp.fetch_client_by_id(creds.id)
            groups = [
                {
                    "id": group.id,
                    "icon_path": group.icon_path
                } for group in client.groups
            ]
            privates = [
                {
                    "id": private.id,
                    "icon_path": private.icon_path,
                    "username": private.username
                } for private in client.privates
            ]

            co_privates = [
                {
                    "id": co_private.id,
                    "icon_path": co_private.icon_path,
                    "username": co_private.username
                } for co_private in client.co_privates
            ]

            contacts = privates + co_privates
            return JSONResponse(content={"groups": groups, "contacts": contacts}, status_code=201)
        
        @self.router.post("/upload_dynamic", response_class=HTMLResponse)
        async def upload_dynamic(request: Request, index: str = Form(...), file: UploadFile = File(...)):
            if request.headers.get('origin') != self.client_server_origin:
                raise HTTPException(status_code=403, detail="Access forbidden.")
            if file.content_type.startswith("image/"):
                filename = f"{index}.jpg"
                save_to = f"{self.storage_images_path}/Dynamic/{filename}"
                try:
                    image = Image.open(io.BytesIO(await file.read()))
                    if image.width > self.max_image_size:
                        ratio = self.max_image_size / image.width
                        image = image.resize((self.max_image_size, int(image.height * ratio)), Image.Resampling.LANCZOS)
                    if image.mode in ('RGBA', 'LA'): image = image.covert('RGB')
                    image.save(save_to, 'JPEG', quality=100)
                except:
                    return JSONResponse(content={"success": False}, status_code=201)
                image_url = f"http://{self.addr[0]}:{self.addr[1]}/images/Dynamic/{filename}"
                status = await self.dmp.save_dynamic(image_url, index, save_to, self.dmp.id())
                if not status: return JSONResponse(content={"success": False}, status_code=201)
                return JSONResponse(content={"url": image_url}, status_code=201)
            return JSONResponse(content={"success": False}, status_code=201)
        
        @self.router.post("/upload_attachement", response_class=HTMLResponse)
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