from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, TypeAdapter, Field as _type
from typing import List, Union, Annotated, Literal
from ast import literal_eval
from PIL import Image
import aiofiles
import json
import jwt
import io
import os

"""
    type: 'group';
    id: number | string;
    owner_id: number | string;
    icon_path: string;
    name: string;
    desc: string;

    async def create_group(self, name: str, client_id: int, id: int, icon_path: str = None, desc: str = None):
    
    type: 'channel';
    id: number | string;
    creator_id: number | string;
    group_id: number | string;
    name: string;

    async def create_channel(self, client_id: int, name: str, id: int, group_id: int = None, private: bool = False, co_client_id: int = None):
    
    type: 'message';
    id: number | string;
    sender_id: number | string;
    group_id: number | string;
    channel_id: number | string;
    sender_name: string;
    sender_icon_path: string;
    content: string;
    unread: boolean;

    async def save_message(self, client_id: int, channel_id: int, content: str, id: int):
    
    type: 'contact';
    id: number | string;
    co_client_id: number | string;
    co_client_name: string;

    type: 'modal';
    id: number | string | null;
    index: string;
    image_select: boolean;
    image_select_path: string | null;
    submit_colour: string;
    fields: Field[];

    type: 'field';
    index: string;
    header: string;
    input_length: string; // short / long
    input: string;
"""

class GrabCreds(BaseModel):
    token: str
    id: int

class Field(BaseModel):
    type: Literal['field']
    index: str
    header: str
    input_length: str
    input: str

class Modal(BaseModel):
    type: Literal['modal']
    id: Union[int, str, None]
    index: str
    image_select: bool
    image_select_path: Union[str, None]
    submit_colour: str
    fields: List[Field]

class Message(BaseModel):
    type: Literal['message']
    id: Union[int, str]
    sender_id: Union[int, str]
    group_id: Union[int, str]
    channel_id: Union[int, str]
    sender_name: str
    sender_icon_path: str
    content: str
    unread: bool

class GroupRequestMembers(BaseModel):
    type: Literal['group_request_members']
    id: Union[int, str]

ClientRequest = Annotated[Union[Modal, Message, GroupRequestMembers], _type(discriminator='type')]

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
            "modal": {"ref": Modal, "func": self.__on_modal},
            "message": {"ref": Message, "func": self.__on_message},
            "group_request_members": {"ref": GroupRequestMembers, "func": self.__on_group_request_members},
        }

        self.system_modal_types = {
            "contact": self.__on_contact,
            "group": self.__on_group,
            "channel": self.__on_channel,
        }

    async def __total_interpreter(self, data: json, socket: WebSocket, id: int):
        adapter = TypeAdapter(ClientRequest)
        request = adapter.validate_python(data)
        if request.type in self.types:
            if isinstance(request, self.types[request.type]["ref"]):
                func = self.types[request.type]["func"]
                response = await func(request, id)
                if response is not None:
                    if isinstance(response, tuple) and len(response) == 2:
                        await socket.send_json(response[0])
                        await socket.send_json(response[1])
                    else: await socket.send_json(response)

    async def __modal_interpreter(self, request, client_id: int):
        if request.index in self.system_modal_types:
            func = self.system_modal_types[request.index]
            response = await func(request, client_id)
            if response is not None:
                return response

    async def __on_modal(self, request, client_id: int):
        response = await self.__modal_interpreter(request, client_id)
        return response

    async def __on_group(self, request, client_id: int):
        id, image_select_path, name, desc = int(request.id), request.image_select_path, next(_ for _ in request.fields if _.index == "name").input, next(_ for _ in request.fields if _.index == "desc").input
        status = await self.dmp.create_group(name, client_id, id // 200, image_select_path, desc) # // for test only!
        if status: return ({
            "type": "group",
            "id": id,
            "owner_id": client_id,
            "icon_path": image_select_path,
            "name": name,
            "desc": desc,
        }, {"type": "modal_status", "status": True, "error": None})
        else: return {"type": "modal_status", "status": False, "error": "Can't create group"}
    
    async def __on_channel(self, request, client_id: int):
        id, group_id, name = int(request.id), int(next(_ for _ in request.fields if _.index == "group_id").input), next(_ for _ in request.fields if _.index == "name").input
        group = await self.dmp.fetch_group_by_id(group_id)
        if group and group is not None:
            status = await self.dmp.create_channel(client_id, name, id, group_id)
            if status:
                request =  {
                    "type": "channel",
                    "id": id,
                    "creator_id": client_id,
                    "group_id": group_id,
                    "name": name,
                }
                await self.cmp.broadcast(request, group.members)
                return (request, {"type": "modal_status", "status": True, "error": None})
            else: return {"type": "modal_status", "status": False, "error": "Can't create channel"}

    async def __on_message(self, request, client_id: int):
        id, sender_id, group_id, channel_id, sender_name, sender_icon_path, content = int(request.id), int(request.sender_id), int(request.group_id), int(request.channel_id), request.sender_name, request.sender_icon_path, request.content
        group = await self.dmp.fetch_group_by_id(group_id)
        if group and group is not None:
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

    async def __on_contact(self, request, client_id: int):
        id, co_client_id, co_client_name = int(request.id), int(next(_ for _ in request.fields if _.index == "co_client_id")), next(_ for _ in request.fields if _.index == "co_client_name")
        status = await self.dmp.create_channel(client_id, co_client_name, id, private=True, co_client_id=co_client_id)
        if status: 
            request = {
                "type": "contact",
                "id": id,
                "co_client_id": co_client_id,
                "co_client_name": co_client_name,
            }
            request_status = await self.cmp.notify(request, co_client_id)
            if not request_status:
                return {"type": "modal_status", "status": False, "error": "An unexpected error occured while sending friend request."}
            return (request, {"type": "modal_status", "status": True, "error": None})
        else: return {"type": "modal_status", "status": False, "error": "Can't friend user."}

    async def __on_group_request_members(self, request, client_id: int):
        id = int(request.id)
        group = await self.dmp.fetch_group_by_id(id)
        if group and group is not None:
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