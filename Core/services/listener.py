from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from ..components.client import NewClient
from ..components.group import NewGroup
from ..components.message import NewMessage
from ..components.permission import NewPermission
from ..components.role import NewRole
from ..components.room import NewRoom
from ..components.space import NewSpace
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal
from ast import literal_eval
from datetime import datetime
from PIL import Image
import aiofiles
import json
import jwt
import io
import os


ClientRequest = Annotated[Union[
    NewClient, 
    NewGroup, 
    NewMessage, 
    NewPermission, 
    NewRole,
    NewRoom,
    NewSpace,
    ], _type(discriminator='type')]

class Clientinterface:
    def __init__(
            self, 
            hasher, 
            dmp, 
            cmp, 
            storage_images_path: str, 
            storage_files_path: str, 
            max_message_length: dict, 
            max_image_size: int, 
            max_file_size: dict, 
            client_server_origin: str, 
            algorithm, access_key, 
            addr: tuple, 
            tepmlates: Jinja2Templates
        ):
        self.addr = addr
        self.access_key = access_key
        self.hasher = hasher
        self.dmp = dmp
        self.cmp = cmp
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
            "new_client": {"ref": NewClient, "func": ...},
            "new_group": {"ref": NewGroup, "func": ...},
            "new_message": {"ref": NewMessage, "func": ...},
            "new_permission": {"ref": NewPermission, "func": ...},
            "new_role": {"ref": NewRole, "func": ...},
            "new_room": {"ref": NewRoom, "func": ...},
            "new_space": {"ref": NewSpace, "func": ...},
        }

    async def __total_interpreter(self, data: json, socket: WebSocket, id: int):
        adapter = TypeAdapter(ClientRequest)
        request = adapter.validate_python(data)
        if request.type in self.types:
            if isinstance(request, self.types[request.type]["ref"]):
                func = self.types[request.type]["func"]
                response = await func(request, id)
                if response is not None:
                    if isinstance(response, tuple):
                        for instance in response: #In case if double, triple, etc (like... really rare, chill)
                            await socket.send_json(instance)
                    else: await socket.send_json(response)

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
        @self.router.websocket("/api")
        async def listener(websocket: WebSocket):
            await websocket.accept()
            id = int(await websocket.receive_text())
            await self.cmp.connect(id, {"socket": websocket})
            try:
                while True:
                    data = await websocket.receive_json()
                    await self.__total_interpreter(data, websocket, id)
            except WebSocketDisconnect:
                await self.cmp.disconnect(id)

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