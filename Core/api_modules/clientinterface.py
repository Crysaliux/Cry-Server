from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from ast import literal_eval
import json
import jwt

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
"""

class GrabCreds(BaseModel):
    token: str
    id: int

class Clientinterface:
    def __init__(self, hasher, dmp, cmp, algorithm, access_key, addr: tuple, tepmlates: Jinja2Templates):
        self.addr = addr
        self.access_key = access_key
        self.hasher = hasher
        self.dmp = dmp
        self.cmp = cmp
        self.templates = tepmlates
        self.algorithm = algorithm
        self.router = APIRouter()

        self.types = {
            "contact": self.__on_contact,
            "group": self.__on_group,
            "channel": self.__on_channel,
            "message": self.__on_message,
        }

    async def __total_interpreter(self, request: dict, socket: WebSocket, id: int):
        if request["type"] in self.types: 
            func = self.types[request["type"]]
            response = await func(request, id)
            if response is not None:
                await socket.send_text(json.dumps(response))

    async def __on_group(self, request: dict, client_id: int):
        id, owner_id, icon_path, name, desc = int(request["id"]), int(request["owner_id"]), request["icon_path"], request["name"], request["desc"]
        status = await self.dmp.create_group(name, owner_id, id, icon_path, desc)
        if status: return {
            "type": "group",
            "id": id,
            "owner_id": owner_id,
            "icon_path": icon_path,
            "name": name,
            "desc": desc,
        }, {"type": "group_creation_status", "status": True, "error": None}
        else: return {"type": "group_creation_status", "status": False, "error": "Can't create group"}
    
    async def __on_channel(self, request: dict, client_id: int):
        id, creator_id, group_id, name = int(request["id"]), int(request["creator_id"]), int(request["group_id"]), request["name"]
        group = await self.dmp.fetch_group_by_id(group_id)
        if group != False and group is not None:
            status = await self.dmp.create_channel(creator_id, name, id, group_id)
            if status:
                request =  {
                    "type": "channel",
                    "id": id,
                    "creator_id": creator_id,
                    "group_id": group_id,
                    "name": name,
                }
                await self.cmp.broadcast(request, group.members)
                return request, {"type": "channel_creation_status", "status": True, "error": None}
            else: return {"type": "channel_creation_status", "status": False, "error": "Can't create channel"}

    async def __on_message(self, request: dict, client_id: int):
        id, sender_id, group_id, channel_id, sender_name, sender_icon_path, content = int(request["id"]), int(request["sender_id"]), int(request["group_id"]), int(request["channel_id"]), request["sender_name"], request["sender_icon_path"], request["content"]
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
                return request, {"type": "message_creation_status", "status": True, "error": None}
            else: return {"type": "message_creation_status", "status": False, "error": "Can't send message."}

    async def __on_contact(self, request: dict, client_id: int):
        id, co_client_id, co_client_name = int(request["id"]), int(request["co_client_id"]), request["co_client_name"]
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
                return {"type": "contact_creation_status", "status": False, "error": "An unexpected error occured while sending friend request."}
            return request, {"type": "contact_creation_status", "status": True, "error": None}
        else: return {"type": "contact_creation_status", "status": False, "error": "Can't friend user."}

    def router_tasks(self):
        @self.router.websocket("/api")
        async def listener(websocket: WebSocket):
            await websocket.accept()
            id = int(await websocket.receive_text())
            await self.cmp.connect(id, {"socket": websocket})
            try:
                while True:
                    data = await websocket.receive_text()
                    await self.__total_interpreter(literal_eval(data), websocket, id)
            except WebSocketDisconnect:
                await self.cmp.disconnect(id)

        @self.router.post("/validate", response_class=HTMLResponse)
        async def validation(request: Request, creds: GrabCreds):
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
        
        @self.router.get("/{id}", response_class=HTMLResponse)
        async def plain(request: Request, id: int):
            sketchy_client = await self.dmp.fetch_client_by_id(id)
            if sketchy_client is not None:
                return self.templates.TemplateResponse("Clientinterface/client.html", 
                                                       {"request": request, 
                                                        "id": id, 
                                                        "icon_path": sketchy_client.icon_path, 
                                                        "username": sketchy_client.username, 
                                                        "addr": f"ws://{self.addr[0]}:{self.addr[1]}/client/listener",
                                                    })
            raise HTTPException(status_code=400)
        
        @self.router.post("/get_id", response_class=HTMLResponse)
        async def get_id(request: Request):
            return JSONResponse(content={"message_id": f"{self.dmp.id()}"}, status_code=201)