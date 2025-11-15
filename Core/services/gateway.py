from fastapi import FastAPI, Request, Form, Header, Cookie, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from pydantic import BaseModel, TypeAdapter, Field as _type, ValidationError
from typing import TypeAlias, Literal
from .worker import Client, Group, Space, Room, Message, Role
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import insert, select, update, delete, exists, and_
from sqlalchemy.orm import selectinload
from ast import literal_eval
from datetime import datetime, timedelta, timezone, date
from jwt import ExpiredSignatureError, InvalidTokenError
from ..components import *
from .permgate import *
from PIL import Image
from functools import wraps
from functools import partial
import aiofiles
from socketio.async_server import AsyncServer
from typing import Union
import asyncio
import uuid
import httpx
import jwt


#Emission types
EmitCommon: TypeAlias = dict[str, str | int | bool | dict[str, str | int | bool]]


class RTMResponse(BaseModel):
    result: dict[str, str | int]
    error: dict[str, str | int]


class GatewayModel(BaseModel):
    body: Union[
        Login,
        Signup,

        CreateGroup,
        EditGroup,
        DeleteGroup,
        
        CreateSpace,
        EditSpace,
        DeleteSpace,

        CreateRoom,
        EditRoom,
        DeleteRoom,
        RelocateRoom,

        CreateMessage,
        EditMessage,
        DeleteMessage,
    ]


class Gateway:
    def __init__(
            self, 
            rtmserver_url,
            rtmserver_access_key,
            hasher, 
            session,  
            ws,
            logger,
            rdserver,
            storage_images_path: str, 
            storage_files_path: str, 
            max_message_length: dict, 
            max_image_size: int, 
            max_file_size: dict, 
            client_server_origin: str, 
            algorithm, access_key, 
            addr: tuple, 
            pg,
        ):
        self.addr = addr
        self.rtmserver_url = rtmserver_url
        self.rtmserver_access_key = rtmserver_access_key
        self.access_key = access_key
        self.hasher = hasher
        self.session = session
        self.ws = ws
        self.rdserver = rdserver
        self.logger = logger
        self.storage_images_path = storage_images_path
        self.storage_files_path = storage_files_path
        self.max_message_length = max_message_length
        self.max_image_size = max_image_size
        self.max_file_size = max_file_size
        self.client_server_origin = client_server_origin
        self.algorithm = algorithm
        self.pg = pg

        self.router = APIRouter()

        self.events = [ #operations: create, edit, delete
            {"name": "login", "handler": self.__signup},
            {"name": "signup", "handler": self.__login},
            {"name": "refresh_session", "handler": self.__refresh_session},

            {"name": "upload_attachement", "handler": self.__upload_attachement},

            {"name": "create_group", "handler": self.__create_group},
            {"name": "edit_group", "handler": self.__edit_group},
            {"name": "delete_group", "handler": self.__delete_group},

            {"name": "create_space", "handler": self.__create_space},
            {"name": "edit_space", "handler": self.__edit_space},
            {"name": "delete_space", "handler": self.__delete_space},

            {"name": "create_room", "handler": self.__create_room},
            {"name": "edit_room", "handler": self.__edit_room},
            {"name": "delete_room", "handler": self.__delete_room},
            {"name": "relocate_room", "handler": self.__relocate_room},

            {"name": "create_message", "handler": self.__create_message},
            {"name": "edit_message", "handler": self.__edit_message},
            {"name": "delete_message", "handler": self.__delete_message},
        ]
        self.__register_events()
        

    def __register_events(self) -> None:
        for event in self.events:
            setattr(self, f"_call_{event["name"]}", self.ws(event["handler"], self.session))
    
    async def run_session_monitor(self) -> None:
        pubsub = self.rdserver.pubsub()
        await pubsub.psubscribe("__keyevent@0__:expired")

        async for message in pubsub.listen():
            key = message.get("data")
            if isinstance(key, (str)):
                client_id = key.split(":")[1]
                await self.__disconnect(client_id)


    async def __call_rtmserver(self, method: str, params: dict[str, str | int | bool | dict[str, str | int | bool]]) -> dict[str, str | int]:
        try: #status, response, error
            async with httpx.AsyncClient() as emission:
                response = await emission.post(
                    self.rtmserver_url,
                    headers={"Authorization": f"apikey {self.rtmserver_access_key}"},
                    json={
                        "method": method, 
                        "params": params,
                    }
                )
                response.raise_for_status()

                try:
                    data = RTMResponse(**response.json())
                    if data.error:
                        return False, None, data.error
                    return True, data.result, None
                except ValidationError: #validation
                    return False, None, ...
        except httpx.RequestError: #network
            return False, None, ...
        
        except Exception as e: #unexpected
            return False, None, ...

        
    def __decode_session_token(self, session_token: str) -> tuple[bool, str | None, str | None, str | None]:
        try:
            payload = jwt.decode(session_token, self.rtmserver_access_key, algorithms=[self.algorithm])
            return True, payload["sub"], payload["ext"]
        except (ExpiredSignatureError, InvalidTokenError):
            return False, None, None
        
    def __decode_refresh_token(self, refresh_token: str) -> tuple[bool, str | None, str | None, str | None, str | None]:
        try:
            payload = jwt.decode(refresh_token, self.access_key, algorithms=[self.algorithm])
            return True, payload["username"], payload["id"], payload["exp"]
        except (ExpiredSignatureError, InvalidTokenError):
            return False, None, None, None
        
    def __encode_session_token(self, id: str) -> str:
        expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())
        
        session_token = jwt.encode(
            {
                "sub": id, 
                "exp": expires_at,
            }, self.rtmserver_access_key, algorithm=self.algorithm)

        return session_token
    
    def __encode_refresh_token(self, id: str, username: str) -> tuple[str, int]:
        expires_at = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        expires_in = int(timedelta(days=7).total_seconds())

        refresh_token = jwt.encode(
            {
                "username": username, 
                "id": id,
                "exp": expires_at,
            }, self.access_key, algorithm=self.algorithm)

        return refresh_token, expires_in
        
    def __construct_response(
            status: bool, 
            body: dict[str, str | dict | int] | None = None, 
            error: str = None
        ) -> EmitCommon:
        return {
            "status": status,
            "body": body,
            "error": error,
        }



    async def __verify_session(self, session_token: str, session) -> tuple[bool, Client | None]:
        status, id, _ = self.__decode_session_token(session_token)
        if not status:
            return False, None

        fetched = await self.rdserver.get(f"client:{id}")
        if fetched == session_token:
            client_res = await session.execute(select(Client).where(Client.id == id))
            client = client_res.scalar_one_or_none()

            if not client:
                self.rdserver.delete(f"client:{id}")
                return False, None
            return True, client
        
        return False, None
    
    async def __verify_refresh(self, refresh_token: str, session) -> tuple[bool, Client | None]:
        status, username, id, expires_at = self.__decode_refresh_token(refresh_token)
        if not status:
            return False, None

        client_res = await session.execute(select(Client).options(
            selectinload(Client.groups),
        ).where(and_(
            Client.username == username,
            Client.id == id, 
            Client.token == refresh_token
        )))
        client = client_res.scalar_one_or_none()

        if not client:
            return False, None
        
        return datetime.now(timezone.utc) <= datetime.fromtimestamp(expires_at, tz=timezone.utc), client



    async def __refresh_session(self, refresh_token: str, session) -> EmitCommon:
        status, client = await self.__verify_refresh(refresh_token, session)
        if not status:
            return self.__construct_response(False, error="...")

        return self.__construct_response(True, {
            "session_token": self.__encode_session_token(client.id)
        })
    
    """
    AUTHENTICATION:
        ...
    """
    
    async def __signup(self, response: Response, body: Signup, session) -> EmitCommon:
        username_exists = await session.execute(select(exists().where(Client.username == body.username))).scalar()
        if username_exists:
            return self.__construct_response(False, error="...")
    
        email_exists = await session.execute(select(exists().where(Client.email == body.email))).scalar()
        if email_exists:
            return self.__construct_response(False, error="...")
    
        datedelta = date.today() - date.fromisoformat(body.date_of_birth)
        if divmod(datedelta.total_seconds(), 31536000)[0] < 13:
            return self.__construct_response(False, error="...")

        id = str(uuid.uuid4())
        refresh_token, expires_in = self.__encode_refresh_token(id, body.username)

        session.add(Client(
            username=body.username,
            nickname=body.username.capitalize(), #CHANGE LATER!!!
            password_hashed=self.hasher.hash(body.password),
            email=body.email,
            date_of_birth=date.fromisoformat(body.date_of_birth),
            token=refresh_token, 
            id=id
        ))
        await session.commit()

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=expires_in,
        )

        session_token = self.__encode_session_token(id)
        await self.rdserver.setex(f"client:{id}", session_token, expires_in)

        return self.__construct_response(True, {
            "session_token": self.__encode_session_token(),
        })
    
    async def __login(self, response: Response, body: Login, session) -> EmitCommon:
        client_res = await session.execute(select(Client).where(Client.email == body.email))
        client = client_res.scalar_one_or_none()

        if not client:
            return self.__construct_response(False, error="...")
        
        if self.hasher.verify(client.password_hashed, body.password):
            refresh_token, expires_in = self.__encode_refresh_token(client.id, client.username)

            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="none",
                max_age=expires_in,
            )

            session_token = self.__encode_session_token(client.id)
            await self.rdserver.setex(f"client:{client.id}", session_token, expires_in)

            return self.__construct_response(True, {
                "session_token": self.__encode_session_token(),
            })
        
    """
    EVENTS:
        ...
    """

    #MEDIA
    async def __upload_attachement(self, session_token: str, file: UploadFile) -> EmitCommon:
        status, _ = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")

        filename = f"{uuid.uuid4()}.{file.filename.split(".")[-1]}"
        data = await file.read()
        
        if file.content_type.startswith("image/"):
            save_to = f"{self.storage_images_path}/{filename}"
            file_url = f"http://{self.addr[0]}:{self.addr[1]}/images/{filename}"
        else:
            save_to = f"{self.storage_files_path}/{filename}"
            file_url = f"http://{self.addr[0]}:{self.addr[1]}/files/{filename}"

        try:
            async with aiofiles.open(save_to, "wb") as buffer:
                await buffer.write(data)
        except:
            return self.__construct_response(False, error="...")
        
        return self.__construct_response(True, {
            "file_url": file_url,
        })

    #GROUP        
    async def __create_group(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")
        
        global_name_exists = await session.execute(select(exists().where(Group.global_name == body.global_name))).scalar()
        if global_name_exists:
            return self.__construct_response(False, error="...")
        
        id, room_id = map(str, [uuid.uuid4() for _ in range(2)])

        session.add(Group(
            owner=client,
            name=body.name,
            globla_name=body.global_name,
            about_group=body.about_group,
            icon_url=body.icon_url,
            rooms=[
                Room(
                    creator=client,
                    name="mega room",
                    about_room="Invincible room",
                    id=room_id,
                )
            ],
            id=id,
        ))
        await session.commit()

        return self.__construct_response(True, {
            "id": id,
            "room_id": room_id,
        })
    
    async def __edit_group(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")
        
        if not await self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.id, client.id, session),
                partial(
                    self.pg.check_global,
                    body.id,
                    client.id,
                    ["CO_OWNER", "MANAGE_GROUP"],
                    "any_of",
                    session
                )
            ]
        )):
            return self.__construct_response(False, error="...")
        
        result = await session.execute(update(Group).where(Group.id == body.id).values(
            name=body.name,
            global_name=body.global_name,
            about_group=body.about_group,
            icon_url=body.icon_url,
            nsfw=body.nsfw,

            content_filter=body.content_filter,
            content_filter_level=body.content_filter_level,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="...")
        
        return self.__construct_response(True)

    async def __delete_group(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")
        
        if not await self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.id, client.id, session),
                partial(
                    self.pg.check_global,
                    body.id,
                    client.id,
                    ["CO_OWNER", "MANAGE_GROUP"],
                    "any_of",
                    session
                )
            ]
        )):
            return self.__construct_response(False, error="...") #owner only!
        
        result = await session.execute(delete(Group).where(Group.id == body.id))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="...")
        
        status, _, error = await self.__call_rtmserver("unsubscribe", {
            "channel": f"${body.id}",  #change later
        })

        if not status:
            return self.__construct_response(False, error=error)

        return self.__construct_response(True)
    

    #SPACE      
    async def __create_space(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")

        group_res = await session.execute(
            select(Group).where(Group.id == body.group_id)
        )
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__construct_response(False, error="...")
        
        if not await self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.group_id, client.id, session),
                partial(
                    self.pg.check_global,
                    body.id,
                    client.id,
                    ["CO_OWNER", "MANAGE_ROOMS"],
                    "any_of",
                    session
                )
            ]
        )):
            return self.__construct_response(False, error="...")

        id = str(uuid.uuid4())

        session.add(Space(
            group=group,
            creator=client,
            name=body.name,
            id=id,
        ))
        await session.commit()

        return self.__construct_response(True, {
            "id": id,
        })
    
    async def __edit_space(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")
        
        if not await self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.group_id, client.id, session),
                partial(
                    self.pg.check_global,
                    body.id,
                    client.id,
                    ["CO_OWNER", "MANAGE_ROOMS"],
                    "any_of",
                    session
                )
            ]
        )):
            return self.__construct_response(False, error="...")
        
        result = await session.execute(update(Space).where(Space.id == body.id).values(
            name=body.name,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="...")
        
        return self.__construct_response(True)

    async def __delete_space(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")
        
        if not await self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.group_id, client.id, session),
                partial(
                    self.pg.check_global,
                    body.id,
                    client.id,
                    ["CO_OWNER", "MANAGE_ROOMS"],
                    "any_of",
                    session
                )
            ]
        )):
            return self.__construct_response(False, error="...") #owner only!
        
        result = await session.execute(delete(Space).where(Space.id == body.id))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="...")
        
        return self.__construct_response(True)
    

    #ROOM    
    async def __create_room(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")

        group_res = await session.execute(
            select(Group).where(Group.id == body.group_id)
        )
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__construct_response(False, error="...")
        
        if not await self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.group_id, client.id, session),
                partial(
                    self.pg.check_global,
                    body.id,
                    client.id,
                    ["CO_OWNER", "MANAGE_ROOMS"],
                    "any_of",
                    session
                )
            ]
        )):
            return self.__construct_response(False, error="...")

        id = str(uuid.uuid4())

        session.add(Room(
            group=group,
            creator=client,
            name=body.name,
            id=id,
        ))
        await session.commit()

        return self.__construct_response(True, {
            "id": id,
        })
    
    async def __edit_room(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")
        
        if not await self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.group_id, client.id, session),
                (
                    "and",
                    [
                        partial(
                            self.pg.check_global,
                            body.group_id,
                            client.id,
                            ["CO_OWNER", "MANAGE_ROOMS"], 
                            "any_of",
                            session
                        ),
                        partial(
                            self.pg.check_rtr,
                            body.id,
                            client.id,
                            ["VIEW_ROOM"], 
                            "must_have",
                            session
                        ),
                    ]
                )
            ]
        )):
            return self.__construct_response(False, error="...")
        
        result = await session.execute(update(Room).where(Room.id == body.id).values(
            name=body.name,
            about_room=body.about_room,
            nsfw=body.nsfw,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="...")
        
        return self.__construct_response(True)

    async def __delete_room(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")
        
        if not self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.group_id, client.id, session),
                (
                    "and",
                    [
                        partial(
                            self.pg.check_global,
                            body.group_id,
                            client.id,
                            ["CO_OWNER", "MANAGE_ROOMS"],
                            "any_of",
                            session
                        ),
                        partial(
                            self.pg.check_rtr,
                            body.id,
                            client.id,
                            ["VIEW_ROOM"],
                            "must_have",
                            session
                        ),
                    ]
                )
            ]
        )):
            return self.__construct_response(False, error="...")
        
        result = await session.execute(delete(Room).where(
            Room.id == body.id,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="...")
        
        status, _, error = await self.__call_rtmserver("unsubscribe", {
            "channel": f"#{body.id}",  #change later
        })

        if not status:
            return self.__construct_response(False, error=error)
        
        return self.__construct_response(True)
    
    async def __relocate_room(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")
        
        space_res = await session.execute(
            select(Space).where(Space.id == body.space_id)
        )
        space = space_res.scalar_one_or_none()

        if not self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.group_id, client.id, session),
                (
                    "and",
                    [
                        partial(
                            self.pg.check_global,
                            body.group_id,
                            client.id,
                            ["CO_OWNER", "MANAGE_ROOMS"],
                            "any_of",
                            session
                        ),
                        partial(
                            self.pg.check_rtr,
                            body.id,
                            client.id,
                            ["VIEW_ROOM"],
                            "must_have",
                            session
                        ),
                    ]
                )
            ]
        )):
            return self.__construct_response(False, error="...")
        
        result = await session.execute(update(Room).where(Room.id == body.id).values(
            space=space,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="...")
        
        return self.__construct_response(True)


    #MESSAGE 
    async def __create_message(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")

        group_res = await session.execute(
            select(Group).where(Group.id == body.group_id)
        )
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__construct_response(False, error="...")
        
        room_res = await session.execute(
            select(Room).where(Room.id == body.room_id)
        )
        room = room_res.scalar_one_or_none()

        if not room:
            return self.__construct_response(False, error="...")
        
        if not self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.group_id, client.id, session),
                (
                    "and",
                    [
                        partial(
                            self.pg.check_global,
                            body.group_id,
                            client.id,
                            ["CO_OWNER", "SEND_MESSAGES"],
                            "any_of",
                            session
                        ),
                        partial(
                            self.pg.check_rtr,
                            body.room_id,
                            client.id,
                            ["VIEW_ROOM", "SEND_MESSAGES"],
                            "must_have",
                            session
                        ),
                    ]
                )
            ]
        )):
            return self.__construct_response(False, error="...")

        id = str(uuid.uuid4())

        session.add(Message(
            group=group,
            room=room,
            author=client,
            content=body.content,
            id=id,
        ))
        await session.commit()

        status, _, error = await self.__call_rtmserver("broadcast", {
            "channel": f"#{body.room_id}",
            "data": {
                "username": client.name,
                "content": body.content,
                "edited": False,
            }
        })

        if not status:
            return self.__construct_response(False, error=error)

        return self.__construct_response(True, {
            "id": id,
        })
    
    async def __edit_message(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")
        
        if not self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.group_id, client.id, session),
                (
                    "and",
                    [
                        partial(
                            self.pg.check_author,
                            body.id,
                            client.id,
                            session
                        ),
                        partial(
                            self.pg.check_rtr,
                            body.room_id,
                            client.id,
                            ["VIEW_ROOM"],
                            "must_have",
                            session
                        )
                    ]
                )
            ]
        )):
            return self.__construct_response(False, error="...")
        
        result = await session.execute(update(Message).where(Message.id == body.id).values(
            content=body.content,
            edited=True,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="...")
        
        return self.__construct_response(True)

    async def __delete_message(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error="...")
        
        if not self.pg.evaluator((
            "or",
            [
                partial(self.pg.check_owner, body.group_id, client.id, session),
                (
                    "and",
                    [
                        partial(
                            self.pg.check_rtr,
                            body.room_id,
                            client.id,
                            ["VIEW_ROOM"],
                            "must_have",
                            session
                        ),
                        (
                            "or",
                            [
                                partial(
                                    self.pg.check_global,
                                    body.group_id,
                                    client.id,
                                    ["DELETE_MESSAGES"],
                                    "must_have",
                                    session
                                ),
                                partial(
                                    self.pg.check_author,
                                    body.id,
                                    client.id,
                                    session
                                ),
                            ]
                        )
                    ]
                )
            ]
        )):
            return self.__construct_response(False, error="...")
        
        result = await session.execute(delete(Message).where(Message.id == body.id))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="...")
        
        return self.__construct_response(True)
    

    def router_tasks(self):
        @self.router.post("/login")
        async def login(response: Response, body: Login):
            return await self._call_login(response, body)
        
        @self.router.post("/signup")
        async def signup(response: Response, body: Signup):
            return await self._call_signup(response, body)
        
        @self.router.post("/refresh_session")
        async def refresh_session(refresh_token: str | None = Cookie(None)):
            return await self._call_refresh_session(refresh_token)
        

        @self.router.post("/upload_attachement")
        async def upload_attachement(request: Request, file: UploadFile = File(...), authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_upload_attachement(session_token, file)
        

        @self.router.post("/create_group")
        async def create_group(request: Request, body: CreateGroup, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_create_group(session_token, body)
        
        @self.router.post("/edit_group")
        async def create_group(request: Request, body: EditGroup, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_edit_group(session_token, body)

        @self.router.post("/delete_group")
        async def create_group(request: Request, body: DeleteGroup, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_delete_group(session_token, body)
        

        @self.router.post("/create_space")
        async def create_group(request: Request, body: CreateSpace, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_create_space(session_token, body)
        
        @self.router.post("/edit_space")
        async def create_group(request: Request, body: EditSpace, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_edit_space(session_token, body)

        @self.router.post("/delete_space")
        async def create_group(request: Request, body: DeleteSpace, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_delete_space(session_token, body)
        

        @self.router.post("/create_room")
        async def create_group(request: Request, body: CreateRoom, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_create_room(session_token, body)
        
        @self.router.post("/edit_room")
        async def create_group(request: Request, body: EditRoom, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_edit_room(session_token, body)

        @self.router.post("/delete_room")
        async def create_group(request: Request, body: DeleteRoom, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_delete_room(session_token, body)


        @self.router.post("/create_message")
        async def create_group(request: Request, body: CreateMessage, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_create_message(session_token, body)
        
        @self.router.post("/edit_message")
        async def create_group(request: Request, body: EditMessage, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_edit_message(session_token, body)

        @self.router.post("/delete_message")
        async def create_group(request: Request, body: DeleteMessage, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_delete_message(session_token, body)