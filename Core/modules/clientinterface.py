from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from ast import literal_eval
import jwt

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

        self.operations = {
            "MessageSend": self.__message_send,
            "MessageDelete": self.__message_delete,
            "MessageEdit": self.__message_edit, #Not fully implemented yet.
            "ChannelCreate": self.__channel_create,
            "ChannelDelete": self.__channel_delete,
            "ChannelEdit": self.__channel_edit, #Not fully implemented yet.
            "GroupCreate": self.__group_create,
            "GroupDelete": self.__group_delete,
            "GroupEdit": self.__group_edit, #Not fully implemented yet.

            "DisplayChannels": self.__channels_get,
            "DisplayMessages": self.__messages_get,
        }

    async def __total_interpreter(self, data: str, socket: WebSocket):
        request = data["request"]
        if request in self.operations:
            func = self.operations[request]
            response = await func(data)
            if response is not None:
                await socket.send_text(response)

    async def __message_send(self, data: dict):
        id, icon_path, content, author_name, author_id, channel_id, group_id = int(data["id"]), data["icon_path"], data["content"], data["author_name"], int(data["author_id"]), int(data["channel_id"]), int(data["group_id"])
        client = await self.dmp.fetch_client_by_id(author_id)
        allowed = any(role.MESSAGE_SEND for role in client.roles if role.group.id == group_id)
        if allowed:
            await self.cmp.message_broadcast(id, icon_path, content, author_name, author_id, channel_id, group_id)
            await self.dmp.save_message(author_id, channel_id, content, id)
        else: return {"request": "Error", "info": "MESSAGE_SEND"}

    async def __message_delete(self, data: dict):
        id, client_id, channel_id, group_id = int(data["id"]), int(data["client_id"]), int(data["channel_id"]), int(data["group_id"])
        message = await self.dmp.fetch_message_by_id(id)
        if message is not None:
            allowed = False
            if message.client.id == client_id:
                allowed = True
            else:
                client = await self.dmp.fetch_client_by_id(client_id)
                allowed = any(role.MESSAGE_DELETE for role in client.roles if role.group.id == group_id)
            if allowed:
                await self.cmp.message_broadcast_removal(id, channel_id)
                check = await self.dmp.delete_message(id)
                if not check: return {"request": "Error", "info": "CANTREMOVE", "object": "MESSAGE"}
            else: return {"request": "Error", "info": "MESSAGE_DELETE"}
        else: return {"request": "Error", "info": "NOTFOUND", "object": "MESSAGE"}
        
    async def __message_edit(self, data: dict):
        id, client_id, channel_id, group_id, new_content = int(data["id"]), int(data["client_id"]), int(data["channel_id"]), int(data["group_id"]), data["new_content"]
        message = await self.dmp.fetch_message_by_id(id)
        if message is not None:
            allowed = False
            if message.client.id == client_id:
                allowed = True
            else:
                client = await self.dmp.fetch_client_by_id(client_id)
                allowed = any(role.MESSAGE_EDIT for role in client.roles if role.group.id == group_id)
            if allowed:
                await self.cmp.message_broadcast_edit(id, channel_id, new_content)
                check = await self.dmp.edit_message(id, new_content)
                if not check: return {"request": "Error", "info": "CANTEDIT", "object": "MESSAGE"}
            else: return {"request": "Error", "info": "MESSAGE_EDIT"}
        else: return {"request": "Error", "info": "NOTFOUND", "object": "MESSAGE"}
        
    async def __channel_create(self, data: dict):
        id, name, group_id, client_id, private, co_client_id  = int(data["id"]), data["name"], int(data["group_id"]), int(data["client_id"]), data["private"], int(data["co_client_id"])
        client = await self.dmp.fetch_client_by_id(client_id)
        if not private:
            allowed = any(role.CHANNEL_CREATE for role in client.roles if role.group.id == group_id)
        else:
            co_client = self.dmp.fetch_client_by_id(co_client_id)
            if not client in co_client.blocked:
                allowed = True
            else: return {"request": "Error", "info": "USERBLOCKED"}
        if allowed:
            if not private:
                group = self.dmp.fetch_group_by_id(group_id)
                await self.cmp.channel_broadcast_creation(id, name, group)
            else:
                await self.dmp.private_channel_broadcast_creation(id, name, client_id, co_client_id)
        else: return {"request": "Error", "info": "CHANNEL_CREATE"}

    async def __channel_delete(self, data: dict):
        id, client_id, group_id, private, co_client_id = int(data["id"]), int(data["client_id"]), int(data["group_id"]), data["private"], int(data["co_client_id"])
        channel = await self.dmp.fetch_channel_by_id(id)
        if channel is not None:
            if not private:
                client = await self.dmp.fetch_client_by_id(client_id)
                allowed = any(role.CHANNEL_DELETE for role in client.roles if role.group.id == group_id)
                if allowed:
                    group = self.dmp.fetch_group_by_id(group_id)
                    await self.cmp.channel_broadcast_removal(id, group)
            else:
                await self.cmp.private_channel_broadcast_removal(id, co_client_id)
                check = await self.dmp.delete_channel(id)
                if not check: return {"request": "Error", "info": "CANTREMOVE", "object": "CHANNEl"}
        else: return {"request": "Error", "info": "NOTFOUND", "object": "CHANNEl"}
        
    async def __channel_edit(self, data: dict):
        id, client_id, group_id, new_name = int(data["id"]), int(data["client_id"]), int(data["group_id"]), data["new_name"]
        channel = await self.dmp.fetch_channel_by_id(id)
        if channel is not None:
            client = await self.dmp.fetch_client_by_id(client_id)
            allowed = any(role.CHANNEL_EDIT for role in client.roles if role.group.id == group_id)
            if allowed:
                group = self.dmp.fetch_group_by_id(group_id)
                await self.cmp.channel_broadcast_edit(id, new_name, group)
                check = await self.dtp.edit_channel(id, new_name)
                if not check: return {"request": "Error", "info": "CANTEDIT", "object": "CHANNEl"}
            else: return {"request": "Error", "info": "CHANNEL_EDIT"}
        else: return {"request": "Error", "info": "NOTFOUND", "object": "CHANNEl"}
        
    async def __group_create(self, data: dict):
        id, client_id, name, icon_path, desc = int(data["id"]), int(data["client_id"]), data["name"], data["icon_path"], data["desc"]
        preset_id, preset_name = await self.dmp.create_group(name, client_id, id, icon_path, desc)
        return {"request": "DisplayCreatedGroup", 
                "id": id, 
                "owner_id": client_id, 
                "name": name, 
                "icon_path": icon_path, 
                "desc": desc, 
                "preset_id": preset_id, 
                "preset_name": preset_name
            }
    
    async def __group_delete(self, data: dict):
        id, client_id = int(data["id"]), int(data["client_id"])
        group = await self.dmp.fetch_group_by_id(id)
        if group is not None:
            if group.owner.id == client_id:
                await self.cmp.group_broadcast_removal(id, group)
                check = await self.dtp.delete_group(id)
                if not check: return {"request": "Error", "info": "CANTREMOVE", "object": "GROUP"}
            else: return {"request": "Error", "info": "GROUP_DELETE"}
        else: return {"request": "Error", "info": "NOTFOUND", "object": "GROUP"}
        
    async def __group_edit(self, data: dict):
        id, client_id, new_name, new_icon_path, new_desc = int(data["id"]), int(data["client_id"]), data["new_name"], data["new_icon_path"], data["mew_desc"]
        to_update = {}
        if new_name is not None: to_update["name"] = new_name
        if new_icon_path is not None: to_update["icon_path"] = new_icon_path
        if new_desc is not None: to_update["desc"] = new_desc

        group = await self.dmp.fetch_group_by_id(id)
        if group is not None:
            allowed = False
            if group.owner.id == client_id:
                allowed = True
            else:
                client = await self.dmp.fetch_client_by_id(client_id)
                allowed = any(role.GROUP_EDIT for role in client.roles if role.group.id == id)
            if allowed:
                await self.cmp.group_broadcast_edit(id, group, **to_update)
                check = await self.dtp.edit_group(id, **to_update)
                if not check: return {"request": "Error", "info": "CANTEDIT", "object": "GROUP"}
            else: return {"request": "Error", "info": "GROUP_EDIT"}
        else: return {"request": "Error", "info": "NOTFOUND", "object": "GROUP"}

    async def __channels_get(self, data: dict):
        group_id = int(data["id"])
        group = await self.dmp.fetch_group_by_id(group_id)
        if group is not None:
            channels = [{"id": channel.id, "name": channel.name, "group_id": group_id} for channel in group.channels]
            if channels is not None:
                channel = await self.dmp.fetch_channel_by_id(channels[0].id)
                messet = [{"id": message.id, 
                           "icon_path": message.client.icon_path, 
                           "content": message.content, 
                           "author_name": message.client.username, 
                           "author_id": message.client.id, 
                           "channel_id": channel.id, 
                           "group_id": group_id
                        } for message in channel.messages]
                messet.reverse()
            return {"request": "DisplayChannels",
                    "group_id": group_id,
                    "channels": channels,
                    "messet": messet
                }
        else: return {"request": "Error", "info": "NOTFOUND", "object": "GROUP"}

    async def __messages_get(self, data: dict):
        channel_id, already_loaded = int(data["id"]), int(data["already_loaded"])
        channel = await self.dmp.fetch_channel_by_id(channel_id)
        if channel is not None:
            index = - (already_loaded + 50)
            unloaded_messages = channel.messages[index:]
            if not unloaded_messages:
                to_load = channel.messages
            else:
                to_load = unloaded_messages
            messet = [{"id": message.id, 
                        "icon_path": message.client.icon_path, 
                        "content": message.content, 
                        "author_name": message.client.username, 
                        "author_id": message.client.id, 
                        "channel_id": channel.id, 
                        "group_id": channel.group.id
                        } for message in to_load]
            messet.reverse()
            return {"request": "DisplayMessages",  
                    "channel_id": channel_id,
                    "messet": messet
                }
        else: return {"request": "Error", "info": "NOTFOUND", "object": "CHANNEL"}


    def router_tasks(self):
        @self.router.websocket("/listener")
        async def listener(websocket: WebSocket):
            await websocket.accept()
            id = int(await websocket.receive_text())
            await self.cmp.connect(id, {"socket": websocket})
            try:
                while True:
                    data = await websocket.receive_text()
                    await self.__total_interpreter(literal_eval(data), websocket)
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
            return JSONResponse(content={}, status_code=201)
        
        @self.router.get("/{id}", response_class=HTMLResponse)
        async def plain(request: Request, id: int):
            sketchy_client = await self.dmp.fetch_client_by_id(id)
            if sketchy_client is not None:
                return self.templates.TemplateResponse("Clientinterface/client.html", 
                                                       {"request": request, 
                                                        "id": id, 
                                                        "icon": sketchy_client.icon_path, 
                                                        "username": sketchy_client.username, 
                                                        "addr": f"ws://{self.addr[0]}:{self.addr[1]}/client/listener",
                                                    })
            raise HTTPException(status_code=400)
        
        @self.router.post("/get_id", response_class=HTMLResponse)
        async def get_id(request: Request):
            return JSONResponse(content={"message_id": f"{self.dmp.id()}"}, status_code=201)