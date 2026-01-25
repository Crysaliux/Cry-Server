"""
The gateway module handles client API requests.

v0.0.2 beta
"""


from fastapi import FastAPI, Request, Form, Header, Cookie, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from pydantic import BaseModel, TypeAdapter, Field as _type, ValidationError
from typing import TypeAlias, Literal
from .worker import Client, Group, Space, Room, Message, Role, GlobalPermission, RoleToRoomPermission, client_group_relationship, banlist_relationship, client_role_relationship, blocked_relationship, to_dict
from .rdserver import RedisDataModel, Fallback
from socketio.async_server import AsyncServer
from socketio.exceptions import ConnectionError, BadNamespaceError, TimeoutError
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
        JoinGroup,
        
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


class Emitter:
    def __init__(self, socket: AsyncServer):
        self.s = socket
        self.body = None
        self.cluster_id = None
        self.status = True
        self.error = None

    async def init_(self, cluster_id: str, body: dict) -> None: #Clear typing later.
        self.body, self.cluster_id = body, cluster_id
        return self
    
    async def __proceed(self, func):
        try:
            await func()
        except ConnectionError:
            self.status, self.error = False, "400"
        except BadNamespaceError:
            self.status, self.error = False, "401"
        except Exception as e:
            self.status, self.error = False, "402"

    async def broadcast(self, event: str, status: bool = True, error: str | None = None):
        if not self.body or not self.cluster_id:
            raise("Can't broadcast, either body or cluster_id are not provided") 
        if not self.status:
            return self
        
        await self.__proceed(
            partial(
                self.s.emit,
                event,
                {
                    "status": status,
                    "body": self.body,
                    "error": error,
                },
                room=self.cluster_id
            )
        )
        return self
        
    async def close(self):
        if not self.body or not self.cluster_id:
            raise("Can't close, either body or cluster_id are not provided") 
        if not self.status:
            return self
        
        await self.__proceed(
            partial(
                self.s.close_room,
                self.cluster_id
            )
        )
        return self
    
    async def join(self, sid):
        if not self.body or not self.cluster_id:
            raise("Can't join, either body or cluster_id are not provided") 
        if not self.status:
            return self
        if not sid:
            self.status, self.error = False, "403"
            return self
        
        await self.__proceed(
            partial(
                self.s.enter_room,
                sid,
                self.cluster_id
            )
        )
        return self
    
    async def done(self):
        return self.status, self.error
    
    async def leave(self, sid):
        if not self.body or not self.cluster_id:
            raise("Can't join, either body or cluster_id are not provided") 
        if not self.status:
            return self
        if not sid:
            self.status, self.error = False, "403"
            return self
        
        await self.__proceed(
            partial(
                self.s.leave_room,
                sid,
                self.cluster_id
            )
        )
        return self
    
    async def done(self):
        return self.status, self.error


class Gateway:
    def __init__(
            self, 
            hasher, 
            session,  
            ws,
            s,
            logger,
            rdserver,
            storage_images_path: str, 
            storage_files_path: str, 
            max_message_length: dict, 
            max_image_size: int, 
            max_file_size: dict, 
            client_server_origin: str, 
            login_expiration: int,
            session_expiration: int,
            heartbeat_delta: int,
            room_cluster_index: str,
            group_cluster_index: str,
            algorithm, 
            access_key, 
            addr: tuple, 
            pg,
        ):
        self.addr = addr
        self.access_key = access_key
        self.hasher = hasher
        self.session = session
        self.ws = ws
        self.s = s
        self.rdserver = rdserver
        self.logger = logger
        self.storage_images_path = storage_images_path
        self.storage_files_path = storage_files_path
        self.max_message_length = max_message_length
        self.max_image_size = max_image_size
        self.max_file_size = max_file_size
        self.client_server_origin = client_server_origin
        self.login_expiration = login_expiration
        self.session_expiration = session_expiration
        self.heartbeat_delta = heartbeat_delta
        self.room_cluster_index = room_cluster_index
        self.group_cluster_index = group_cluster_index
        self.algorithm = algorithm
        self.pg = pg

        self.router = APIRouter()
        self.s.on("connect", self.__connect)

        self.events = [ #operations: create, edit, delete
            {"name": "login", "handler": self.__signup},
            {"name": "signup", "handler": self.__login},
            {"name": "refresh_session", "handler": self.__refresh_session},

            {"name": "upload_attachement", "handler": self.__upload_attachement},

            {"name": "create_group", "handler": self.__create_group},
            {"name": "edit_group", "handler": self.__edit_group},
            {"name": "delete_group", "handler": self.__delete_group},
            {"name": "join_group", "handler": self.__join_group},
            {"name": "leave_group", "handler": self.__leave_group},
            {"name": "ban_client", "handler": self.__ban_client},
            {"name": "kick_client", "handler": self.__kick_client},
            {"name": "view_group_settings", "handler": self.__view_group_settings},
            {"name": "view_group_roles", "handler": self.__view_group_roles},
            {"name": "view_banned", "handler": self.__view_banned},

            {"name": "create_space", "handler": self.__create_space},
            {"name": "edit_space", "handler": self.__edit_space},
            {"name": "delete_space", "handler": self.__delete_space},
            {"name": "view_space_settings", "handler": self.__view_space_settings},

            {"name": "create_room", "handler": self.__create_room},
            {"name": "edit_room", "handler": self.__edit_room},
            {"name": "delete_room", "handler": self.__delete_room},
            {"name": "relocate_room", "handler": self.__relocate_room},
            {"name": "join_room", "handler": self.__join_room},
            {"name": "view_room_settings", "handler": self.__view_room_settings},

            {"name": "create_message", "handler": self.__create_message},
            {"name": "edit_message", "handler": self.__edit_message},
            {"name": "delete_message", "handler": self.__delete_message},

            {"name": "block_client", "handler": self.__block_client},
            {"name": "view_client", "handler": self.__view_client},
            {"name": "view_profile_settings", "handler": ...},
            {"name": "view_blocked", "handler": ...},
            {"name": "view_group", "handler": ...},
            {"name": "view_room", "handler": ...},
        ]
        self.__register_events()
        

    def __register_events(self) -> None:
        for event in self.events:
            setattr(self, f"_call_{event["name"]}", self.ws(event["handler"], self.session))

        
    def __decode_session_token(self, session_token: str) -> tuple[bool, str | None, str | None, str | None]:
        try:
            payload = jwt.decode(session_token, self.rtmserver_access_key, algorithms=[self.algorithm])
            return True, payload["sub"], payload["ext"]
        except (ExpiredSignatureError, InvalidTokenError):
            return False, None, None
        
    def __decode_refresh_token(self, refresh_token: str) -> tuple[bool, str | None, str | None, str | None, str | None]:
        try:
            payload = jwt.decode(refresh_token, self.access_key, algorithms=[self.algorithm])
            return True, payload["sub"], payload["exp"]
        except (ExpiredSignatureError, InvalidTokenError):
            return False, None, None
        
    def __encode_session_token(self, id: str) -> str:
        expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=self.session_expiration)).timestamp())
        
        session_token = jwt.encode(
            {
                "sub": id, 
                "exp": expires_at,
            }, self.rtmserver_access_key, algorithm=self.algorithm)

        return session_token
    
    def __encode_refresh_token(self, id: str) -> tuple[str, int]:
        expires_at = int((datetime.now(timezone.utc) + timedelta(days=self.login_expiration)).timestamp())
        expires_in = int(timedelta(days=self.login_expiration).total_seconds())

        refresh_token = jwt.encode(
            {
                "sub": id,
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


    async def __verify_session(self, session_token: str) -> tuple[bool, RedisDataModel | None]:
        status, id, expires_at = self.__decode_session_token(session_token)
        if not status:
            return False, None, "313"
        
        if datetime.now(timezone.utc) > datetime.fromtimestamp(expires_at, tz=timezone.utc):
            return False, None, "301"

        status, client, error = await self.rdserver.get_(f"client:{id}")
        if not status:
            return False, None, error
        if not client:
            return False, None, "305"
        if client.session_token != session_token:
            return False, None, "314"
        return True, client, None
    
    async def __verify_refresh(self, refresh_token: str, session) -> tuple[bool, str | None, str | None]:
        status, id, expires_at = self.__decode_refresh_token(refresh_token)
        if not status:
            return False, None, "315"

        if datetime.now(timezone.utc) > datetime.fromtimestamp(expires_at, tz=timezone.utc):
            return False, None, "316"

        fallback = Fallback(session, self.rdserver)
        status, _, error = await fallback.client_(id, self.pg, refresh_token, True)
        if not status:
            return False, None, error
        return True, id, None
        
    async def __verify_group(self, session, **kwargs):
        fallback = Fallback(session, self.rdserver)
        status, group, error = await fallback.group_(**kwargs)
        return status, group, error

    """
    REFRESHER
    """

    async def __refresh_session(self, refresh_token: str, session) -> EmitCommon:
        status, id, error = await self.__verify_refresh(refresh_token, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        session_token = self.__encode_session_token(id)

        status, error = await self.rdserver.update_(f"client:{id}", {"session_token": session_token})
        if not status:
            return self.__construct_response(False, error=error)

        return self.__construct_response(True, {
            "session_token": self.__encode_session_token(id),
            "wait_for": self.heartbeat_delta,
        })
    
    """
    AUTHENTICATION:
        ...
    """
    
    async def __signup(self, response: Response, body: Signup, session) -> EmitCommon:
        username_exists = await session.execute(select(exists().where(Client.username == body.username))).scalar()
        if username_exists:
            return self.__construct_response(False, error="302")
    
        email_exists = await session.execute(select(exists().where(Client.email == body.email))).scalar()
        if email_exists:
            return self.__construct_response(False, error="303")
    
        datedelta = date.today() - date.fromisoformat(body.date_of_birth)
        if divmod(datedelta.total_seconds(), 31536000)[0] < 13:
            return self.__construct_response(False, error="304")

        id = str(uuid.uuid4())
        refresh_token, expires_in = self.__encode_refresh_token(id)
        password_hashed, dob = self.hasher.hash(body.password), date.fromisoformat(body.date_of_birth)

        session.add(Client(
            username=body.username,
            nickname=body.username.capitalize(), #CHANGE LATER!!!
            password_hashed=password_hashed,
            email=body.email,
            date_of_birth=dob,
            refresh_token=refresh_token,
            id=id
        ))
        await session.commit()

        model = RedisDataModel(**{
            "username": body.username,
            "nickname": body.nickname,
            "password": password_hashed,
            "email": body.email,
            "date_or_birth": dob,
            "blocked": [],

            "refresh_token": refresh_token,
            "roles": {}, # "role_id": "group_id"
            "permissions": {
                "groups": {}, # "group_id": [..]
                "rooms": {},# "room_id": [...]
            },
            "sid": None,
            "id": id,
        })

        await self.rdserver.set_(
            f"client:{id}",
            model,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=expires_in,
        )

        return self.__construct_response(True, {
            "session_token": self.__encode_session_token(id),
            "wait_for": self.heartbeat_delta,
        })
    
    async def __login(self, response: Response, body: Login, session) -> EmitCommon:
        client_res = await session.execute(select(Client).where(Client.email == body.email))
        client = client_res.scalar_one_or_none()

        if not client:
            return self.__construct_response(False, error="318")
        """
        We return 318 (invalid credentials) here as we fetch client by email
        """
        
        if not self.hasher.verify(client.password_hashed, body.password):
            return self.__construct_response(False, error="318")

        refresh_token, expires_in = self.__encode_refresh_token(client.id)
        
        client.refresh_token = refresh_token
        await session.commit() #will work?

        blocked_res = (
            select(blocked_relationship.c.blocked_id)
            .where(blocked_relationship.c.client_id == client.id)
        )
        blocked = await session.scalars(blocked_res).all()

        model = RedisDataModel(**{
            "username": client.username,
            "nickname": client.nickname,
            "password": body.password,
            "email": body.email,
            "date_or_birth": client.date_of_birth,
            "blocked": blocked,

            "refresh_token": refresh_token,
            "roles": {}, # "role_id": "group_id"
            "permissions": {
                "groups": {}, # "group_id": [..]
                "rooms": {},# "room_id": [...]
            },
            "sid": None,
            "id": client.id,
        })
            
        await self.rdserver.set_(
            f"client:{client.id}",
            model,
        )

        #Fetching permissions related data (roles, permissions)
        status, error = await self.pg.fetch_on_load(client.id, session)
        if not status:
            return self.__construct_response(False, error=error)

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=expires_in,
        )

        return self.__construct_response(True, {
            "session_token": self.__encode_session_token(client.id),
            "wait_for": self.heartbeat_delta,
        })
    
    """
    SOCKET CONNECTION
    """

    async def __connect(self, sid, environ, auth) -> Literal[False] | EmitCommon:
        try: session_token = auth["session_token"]
        except KeyError:
            return False
        
        status, client, _ = await self.__verify_session(session_token) #error to terminal!
        if not status:
            return False
        
        status, error = await self.rdserver.update_(f"client:{client.id}", {
            "sid": sid,
        })
        if not status:
            return self.__construct_response(False, error=error)

        await self.gateway.save_session(sid, {"id": client.id})

        
    """
    EVENTS:
        ...
    """

    #MEDIA
    async def __upload_attachement(self, session_token: str, file: UploadFile) -> EmitCommon:
        status, _, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)

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
            return self.__construct_response(False, error="310")
        
        return self.__construct_response(True, {
            "file_url": file_url,
        })

    #GROUP        
    async def __create_group(self, session_token: str, body: CreateGroup, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        global_name_exists = await session.execute(select(exists().where(Group.global_name == body.global_name))).scalar()
        if global_name_exists:
            return self.__construct_response(False, error="311")
        
        id, room_id, role_id, owner_perm_id, everyone_perm_id = map(str, [uuid.uuid4() for _ in range(5)])

        session.add(Group(
            owner_id=client.id,
            name=body.name,
            globla_name=body.global_name,
            about_group=body.about_group,
            icon_url=body.icon_url,
            rooms=[
                Room(
                    creator_id=client.id,
                    name="mega room",
                    about_room="Invincible room",
                    id=room_id,
                )
            ],
            roles=[
                Role(
                    name="owner",
                    id=role_id,
                    global_permissions=[
                        GlobalPermission(
                            name="OWNER",
                            id=owner_perm_id,
                        ),
                        GlobalPermission(
                            name="EVERYONE",
                            id=everyone_perm_id,
                        )
                    ],
                )
            ],
            id=id,
        ))
        await session.commit()

        model = RedisDataModel(**{
            "id": id
        })

        status, error = await self.rdserver.set_(f"globalname:{body.global_name}", model)
        if not status:
            return False, None, error

        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{id}", {}).join(client.sid).done()
        if not status:
            return self.__construct_response(False, error=error)

        return self.__construct_response(True, {
            "id": id,
            "room_id": room_id,
        })
    
    async def __edit_group(self, session_token: str, body: EditGroup, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(session, group_id=body.id)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.id, 
            ["OWNER", "CO_OWNER", "MANAGE_GROUPS"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        result = await session.execute(update(Group).where(Group.id == body.id).values(
            name=body.name,
            about_group=body.about_group,
            icon_url=body.icon_url,
            nsfw=body.nsfw,

            content_filter=body.content_filter,
            content_filter_level=body.content_filter_level,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="306")
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{body.id}", {
            "name": body.name,
            "about_group": body.about_group,
            "icon_url": body.icon_url,
            "nsfw": body.nsfw,

            "content_filter": body.content_filter,
            "content_filter_level": body.content_filter_level,

            "id": body.id,
        }).broadcast("group_edited").done()

        if not status:
            return self.__construct_response(False, error=error)
        
        return self.__construct_response(True)

    async def __delete_group(self, session_token: str, body: DeleteGroup, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(session, group_id=body.id)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.id, 
            ["OWNER"], 
            "must_have",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312") #add globalname deletion!

        status, error = await self.rdserver.delete_(f"globalname:{group.global_name}")
        if not status:
            return self.__construct_response(False, error=error)
        
        status, error = await self.pg.cleanup(body.id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{body.id}", {
            "id": body.id,
        }).broadcast("group_deleted").close().done()
        if not status:
            return self.__construct_response(False, error=error)
        
        return self.__construct_response(True)

    async def __join_group(self, session_token: str, body: JoinGroup, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(session, global_name=body.global_name)
        if not status:
            return self.__construct_response(False, error=error)

        if client.id in group.banned:
            return self.__construct_response(False, error="322")

        status, error = await self.rdserver.update_(f"group:{body.id}", {
            "members": group.members + [client.id]
        })
        if not status:
            return self.__construct_response(False, error=error)
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.room_cluster_index}{group.rooms[0]}", {
            "nickname": client.nickname,
            "id": client.id,
        }).broadcast("group_joined").done()
        if not status:
            return self.__construct_response(False, error=error)
        
        status, error = await emt.init_(f"{self.group_cluster_index}{body.id}", {}).join(client.sid).done()
        if not status:
            return self.__construct_response(False, error=error)
        
        rooms_res = await session.execute(
            select(Room.id, Room.name)
            .join(Group.rooms)
            .join(Group.members)
            .where(
                Client.id == client.id,
                exists(
                    select(1)
                    .select_from(RoleToRoomPermission)
                    .join(
                        client_role_relationship,
                        client_role_relationship.c.client_id == client.id
                    )
                    .where(
                        client_role_relationship.c.role_id == RoleToRoomPermission.role_id,
                        RoleToRoomPermission.room_id == Room.id,
                        RoleToRoomPermission.name == "VIEW_ROOM",
                    )
                ),
            ).distinct()
        )
        rooms = rooms_res.all()

        #members!!!
        
        return self.__construct_response(True, {
            "name": group.name,
            "global_name": group.global_name,
            "about_group": group.about_group,
            "icon_url": group.icon_url,
            "members": ...,
            "rooms": rooms
        })
    
    async def __leave_group(self, session_token: str, body: LeaveGroup, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(session, group_id=body.id)
        if not status:
            return self.__construct_response(False, error=error)

        if not client.id in group.members:
            return self.__construct_response(False, error="323")

        status, error = await self.rdserver.update_(f"group:{body.id}", {
            "members": group.members - [client.id]
        })
        if not status:
            return self.__construct_response(False, error=error)
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.room_cluster_index}{group.rooms[0]}", {
            "nickname": client.nickname,
            "id": client.id,
        }).broadcast("group_left").done()
        if not status:
            return self.__construct_response(False, error=error)
        
        status, error = await emt.init_(f"{self.group_cluster_index}{body.id}", {}).leave(client.sid).done()
        if not status:
            return self.__construct_response(False, error=error)

        return self.__construct_response(True)
    
    async def __ban_client(self, session_token: str, body: BanClient, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(session, group_id=body.id)
        if not status:
            return self.__construct_response(False, error=error)

        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        if not body.client_id in group.members:
            return self.__construct_response(False, error="324")
        
        if body.client_id in group.banned:
            return self.__construct_response(False, error="325")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.id, 
            ["OWNER", "CO_OWNER", "BAN"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        fallback = Fallback(session, self.rdserver)
        status, culprit, error = await fallback.client_(body.client_id)
        if not status:
            return self.__construct_response(False, error=error)
        if not culprit:
            return self.__construct_response(False, error="305")
        
        result = await session.execute(delete(client_group_relationship).where(
            and_(
                client_group_relationship.c.client_id == body.client_id,
                client_group_relationship.c.group_id == body.id
            )
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="323")
        
        await session.execute(
            insert(banlist_relationship).values(
                client_id=body.client_id,
                group_id=body.id,
            )
        )
        await session.commit()

        status, error = await self.rdserver.update_(f"group:{body.id}", {
            "members": group.members - [body.id]
        })
        if not status:
            return self.__construct_response(False, error=error)
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{body.id}", {
            "id": body.client_id,
        }).broadcast("client_banned").leave(culprit.sid).done()
        if not status:
            return self.__construct_response(False, error=error)

        return self.__construct_response(True)
    
    async def __kick_client(self, session_token: str, body: KickClient, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(session, group_id=body.id)
        if not status:
            return self.__construct_response(False, error=error)

        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        if not body.client_id in group.members:
            return self.__construct_response(False, error="324")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.id, 
            ["OWNER", "CO_OWNER", "KICK"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        fallback = Fallback(session, self.rdserver)
        status, culprit, error = await fallback.client_(body.client_id)
        if not status:
            return self.__construct_response(False, error=error)
        if not culprit:
            return self.__construct_response(False, error="305")
        
        result = await session.execute(delete(client_group_relationship).where(
            and_(
                client_group_relationship.c.client_id == body.client_id,
                client_group_relationship.c.group_id == body.id
            )
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="323")

        status, error = await self.rdserver.update_(f"group:{body.id}", {
            "members": group.members - [body.id]
        })
        if not status:
            return self.__construct_response(False, error=error)
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{body.id}", {
            "id": body.client_id,
        }).broadcast("client_kicked").leave(culprit.sid).done()
        if not status:
            return self.__construct_response(False, error=error)

        return self.__construct_response(True)
    
    async def __view_group_settings(self, session_token: str, body: ViewGroupSettings, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(session, group_id=body.id)
        if not status:
            return self.__construct_response(False, error=error)

        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.id, 
            ["OWNER", "CO_OWNER", "MANAGE_GROUP"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")

        return self.__construct_response(True, {
            "name": group.name,
            "global_name": group.global_name,
            "about_group": group.about_group,
            "icon_url": group.icon_url,
            "nsfw": group.nsfw,
            "content_filter": group.content_filter,
            "content_filter_level": group.content_filter_level,
            "id": body.id,
        })
    
    async def __view_group_roles(self, session_token: str, body: ViewGroupRoles, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(session, group_id=body.id)
        if not status:
            return self.__construct_response(False, error=error)

        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.id, 
            ["OWNER", "CO_OWNER", "MANAGE_GROUP"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        roles_res = await self.session.execute(
            select(Role.id, Role.name, Role.color)
            .join(Group.roles)
            .where(Group.id == body.id)
        )
        roles = roles_res.all()

        return self.__construct_response(True, {
            "roles": roles, #returns a list of lists [id, nickname, avatar_url]
            "id": body.id,
        })
    
    async def __view_banned(self, session_token: str, body: ViewBanned, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(session, group_id=body.id)
        if not status:
            return self.__construct_response(False, error=error)

        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.id, 
            ["OWNER", "CO_OWNER", "MANAGE_GROUP"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        banned_res = await self.session.execute(
            select(Client.id, Client.nickname, Client.avatar_url)
            .join(Group.banned)
            .where(Group.id == body.id)
        )
        banned = banned_res.all()

        return self.__construct_response(True, {
            "banned": banned, #returns a list of lists [id, nickname, avatar_url]
            "id": body.id,
        })
    

    #SPACE      
    async def __create_space(self, session_token: str, body: CreateSpace, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")

        group_res = await session.execute(
            select(Group).where(Group.id == body.group_id)
        )
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__construct_response(False, error="306")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.group_id, 
            ["OWNER", "CO_OWNER", "MANAGE_ROOMS"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")

        id = str(uuid.uuid4())

        session.add(Space(
            creator_id=client.id,
            group=group,
            name=body.name,
            id=id,
        ))
        await session.commit()

        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{body.group_id}", {
            "name": body.name,
            "id": id,
        }).broadcast("space_created").done()
        if not status:
            return self.__construct_response(False, error=error)

        return self.__construct_response(True, {
            "id": id,
        })
    
    async def __edit_space(self, session_token: str, body: EditSpace, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.group_id, 
            ["OWNER", "CO_OWNER", "MANAGE_ROOMS"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        result = await session.execute(update(Space).where(Space.id == body.id).values(
            name=body.name,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="307")
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{body.group_id}", {
            "name": body.name,
            "id": body.id,
        }).broadcast("space_edited").done()
        if not status:
            return self.__construct_response(False, error=error)
        
        return self.__construct_response(True)

    async def __delete_space(self, session_token: str, body: DeleteSpace, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.group_id, 
            ["OWNER", "CO_OWNER", "MANAGE_ROOMS"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        result = await session.execute(delete(Space).where(Space.id == body.id))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="307")
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{body.group_id}", {
            "id": body.id,
        }).broadcast("space_deleted").done()
        if not status:
            return self.__construct_response(False, error=error)
        
        return self.__construct_response(True)
    
    async def __view_space_settings(self, session_token: str, body: ViewSpaceSettings, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.group_id, 
            ["OWNER", "CO_OWNER", "MANAGE_ROOMS"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        name_res = await self.session.execute(
            select(Space.name)
            .where(Space.id == body.id)
        )
        name = name_res.scalars_one_or_none()
        
        return self.__construct_response(True, {
            "name": name,
            "id": body.id,
        })
    

    #ROOM    
    async def __create_room(self, session_token: str, body: CreateRoom, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")

        group_res = await session.execute(
            select(Group).where(Group.id == body.group_id)
        )
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__construct_response(False, error="306")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.group_id, 
            body.id, 
            ["OWNER", "CO_OWNER", "MANAGE_ROOMS"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")

        id = str(uuid.uuid4())

        session.add(Room(
            creator_id=client.id,
            group=group,
            name=body.name,
            about_room=body.about_room,
            space_id=body.space_id,
            id=id,
        ))
        await session.commit()

        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{body.group_id}", {
            "name": body.name,
            "about_room": body.about_room,
            "space_id": body.space_id,
            "id": body.id,
        }).broadcast("room_created").done()
        if not status:
            return self.__construct_response(False, error=error)
        
        status, error = await emt.init_(f"{self.room_cluster_index}{id}", {}).join(client.sid).done()
        if not status:
            return self.__construct_response(False, error=error)

        return self.__construct_response(True, {
            "id": id,
        })
    
    async def __edit_room(self, session_token: str, body: EditRoom, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator((
            "or",
            [
                partial(
                    self.pg.check_global, 
                    client.id, 
                    body.group_id, 
                    ["OWNER", "CO_OWNER"], 
                    "any_of"
                ),
                (
                    "and",
                    [
                        partial(
                            self.pg.check_global,
                            client.id,
                            body.group_id,
                            ["MANAGE_GROUPS"],
                            "must_have",
                        ),
                        partial(
                            self.pg.check_rtr,
                            client.id,
                            body.room_id,
                            ["VIEW_ROOM"],
                            "must_have",
                        )
                    ]
                )
            ]
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        result = await session.execute(update(Room).where(Room.id == body.id).values(
            name=body.name,
            about_room=body.about_room,
            nsfw=body.nsfw,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="308")
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{body.group_id}", {
            "name": body.name,
            "about_room": body.about_room,
            "id": body.id,
        }).broadcast("room_edited").done()
        if not status:
            return self.__construct_response(False, error=error)
        
        return self.__construct_response(True)

    async def __delete_room(self, session_token: str, body: DeleteRoom, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator((
            "or",
            [
                partial(
                    self.pg.check_global, 
                    client.id, 
                    body.group_id, 
                    ["OWNER", "CO_OWNER"], 
                    "any_of"
                ),
                (
                    "and",
                    [
                        partial(
                            self.pg.check_global,
                            client.id,
                            body.group_id,
                            ["MANAGE_GROUPS"],
                            "must_have",
                        ),
                        partial(
                            self.pg.check_rtr,
                            client.id,
                            body.room_id,
                            ["VIEW_ROOM"],
                            "must_have",
                        )
                    ]
                )
            ]
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        result = await session.execute(delete(Room).where(
            Room.id == body.id,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="308")
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{body.group_id}", {
            "id": body.id,
        }).broadcast("room_deleted").done()
        if not status:
            return self.__construct_response(False, error=error)
        
        status, error = await emt.init_(f"{self.room_cluster_index}{body.id}", {}).close().done()
        if not status:
            return self.__construct_response(False, error=error)
        
        return self.__construct_response(True)
    
    async def __relocate_room(self, session_token: str, body: RelocateRoom, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        space_res = await session.execute(
            select(Space).where(Space.id == body.space_id)
        )
        space = space_res.scalar_one_or_none()
        
        if not space:
            return self.__construct_response(False, error="307")
        
        status, allowed, error = await self.pg.evaluator((
            "or",
            [
                partial(
                    self.pg.check_global, 
                    client.id, 
                    body.group_id, 
                    ["OWNER", "CO_OWNER"], 
                    "any_of"
                ),
                (
                    "and",
                    [
                        partial(
                            self.pg.check_global,
                            client.id,
                            body.group_id,
                            ["MANAGE_GROUPS"],
                            "must_have",
                        ),
                        partial(
                            self.pg.check_rtr,
                            client.id,
                            body.room_id,
                            ["VIEW_ROOM"],
                            "must_have",
                        )
                    ]
                )
            ]
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        result = await session.execute(update(Room).where(Room.id == body.id).values(
            space=space,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="308")
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{body.group_id}", {
            "space_id": body.space_id,
            "id": body.id,
        }).broadcast("room_relocated").done()
        if not status:
            return self.__construct_response(False, error=error)
        
        return self.__construct_response(True)
    
    async def __join_room(self, session_token: str, body: JoinRoom, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(session, id=body.group_id)
        if not status:
            return self.__construct_response(False, error=error)

        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator((
            "or",
            [
                partial(
                    self.pg.check_global, 
                    client.id, 
                    body.group_id, 
                    ["OWNER", "CO_OWNER"], 
                    "any_of"
                ),    
                partial(
                    self.pg.check_rtr,
                    client.id,
                    body.room_id,
                    ["VIEW_ROOM"],
                    "must_have",
                )      
            ]
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.room_cluster_index}{body.id}", {}).join(client.sid).done()
        if not status:
            return self.__construct_response(False, error=error)
        
        return self.__construct_response(True)
    
    async def __view_room_settings(self, session_token: str, body: ViewRoomSettings, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator(partial(
            self.pg.check_global, 
            client.id, 
            body.group_id, 
            ["OWNER", "CO_OWNER", "MANAGE_ROOMS"], 
            "any_of",
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        name_res = await self.session.execute(
            select(Room.name, Room.about_room, Room.nsfw)
            .where(Room.id == body.id)
        )
        name, about_room, nsfw = name_res.one()
        
        return self.__construct_response(True, {
            "name": name,
            "about_room": about_room,
            "nsfw": nsfw,
            "id": body.id,
        })


    #MESSAGE 
    async def __create_message(self, session_token: str, body: CreateMessage, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")

        group_res = await session.execute(
            select(Group).where(Group.id == body.group_id)
        )
        group = group_res.scalar_one_or_none()

        if not group:
            return self.__construct_response(False, error="306")
        
        room_res = await session.execute(
            select(Room).where(Room.id == body.room_id)
        )
        room = room_res.scalar_one_or_none()

        if not room:
            return self.__construct_response(False, error="308")
        
        status, allowed, error = await self.pg.evaluator((
            "or",
            [
                partial(
                    self.pg.check_global, 
                    client.id, 
                    body.group_id, 
                    ["OWNER", "CO_OWNER"], 
                    "any_of"
                ),
                (
                    "and",
                    [
                        partial(
                            self.pg.check_global,
                            client.id,
                            body.group_id,
                            ["SEND_MESSAGES"],
                            "must_have"
                        ),
                        partial(
                            self.pg.check_rtr,
                            client.id,
                            body.room_id,
                            ["SEND_MESSAGES", "VIEW_ROOM"],
                            "must_have"
                        )
                    ]
                )
                       
            ]
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")

        id = str(uuid.uuid4())

        session.add(Message(
            group=group,
            room=room,
            author=client,
            content=body.content,
            id=id,
        ))
        await session.commit()

        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.room_cluster_index}{body.room_id}", {
            "username": client.name,
            "content": body.content,
            "edited": False,
            "id": id,
        }).broadcast("message_created").done()
        if not status:
            return self.__construct_response(False, error=error)

        return self.__construct_response(True, {
            "id": id,
        })
    
    async def __edit_message(self, session_token: str, body: EditMessage, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token) #ponder...
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        if not await self.pg.check_author(client.id, body.id, session):
            return self.__construct_response(False, error="312")
        
        result = await session.execute(update(Message).where(Message.id == body.id).values(
            content=body.content,
            edited=True,
        ))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="309")
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.room_cluster_index}{body.room_id}", {
            "content": body.content,
            "edited": True,
            "id": body.id,
        }).broadcast("message_edited").done()
        if not status:
            return self.__construct_response(False, error=error)
        
        return self.__construct_response(True)

    async def __delete_message(self, session_token: str, body: DeleteMessage, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not client.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, allowed, error = await self.pg.evaluator((
            "or",
            [
                partial(
                    self.pg.check_global, 
                    client.id, 
                    body.group_id, 
                    ["OWNER", "CO_OWNER"], 
                    "any_of"
                ),
                (
                    "and",
                    [
                        partial(
                            self.pg.check_global,
                            client.id,
                            body.group_id,
                            ["DELETE_MESSAGES"],
                            "must_have"
                        ),
                        partial(
                            self.pg.check_rtr,
                            client.id,
                            body.room_id,
                            ["DELETE_MESSAGES", "VIEW_ROOM"],
                            "must_have"
                        )
                    ]
                )
                       
            ]
        ))
        if not status:
            return self.__construct_response(False, error=error)
        if not allowed:
            return self.__construct_response(False, error="312")
        
        result = await session.execute(delete(Message).where(Message.id == body.id))

        if result.rowcount() == 0:
            return self.__construct_response(False, error="309")
        
        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.room_cluster_index}{body.room_id}", {
            "id": body.id,
        }).broadcast("message_deleted").done()
        if not status:
            return self.__construct_response(False, error=error)
        
        return self.__construct_response(True)
    

    #CLIENT
    async def __block_client(self, session_token: str, body: BlockClient, session) -> EmitCommon:
        status, client, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        await session.execute(
            blocked_relationship.insert(),
            {
                "client_id": client.id,
                "blocked_id": body.id,
            }
        )
        await session.commit()
        
        status, error = await self.rdserver.update_(f"client:{client.id}", {
            "banned": client.banned + [body.id]
        })
        if not status:
            return False, None, error

        emt = Emitter(self.s)
        status, error = await emt.init_(f"{self.group_cluster_index}{id}", {}).join(client.sid).done()
        if not status:
            return self.__construct_response(False, error=error)

        return self.__construct_response(True)
    
    async def __view_client(self, session_token: str, body: ViewClient, session) -> EmitCommon:
        status, _, error = await self.__verify_session(session_token)
        if not status:
            return self.__construct_response(False, error=error)
        
        status, group, error = await self.__verify_group(body.group_id, session)
        if not status:
            return self.__construct_response(False, error=error)
        
        if not body.id in group.members:
            return self.__construct_response(False, error="323")
        
        status, client, error = await self.rdserver.get_(f"client:{body.id}")
        if not status:
            return self.__construct_response(False, error=error)
        if not client:
            return self.__construct_response(False, error="305")
        return self.__construct_response(True, {
            "username": client.username,
            "named_roles": ...,
        }) #might need named_roles field.
    

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
        
        @self.router.post("/join_group")
        async def create_group(request: Request, body: JoinGroup, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_join_group(session_token, body)
        
        @self.router.post("/leave_group")
        async def create_group(request: Request, body: LeaveGroup, authorization: str = Header(...)):
            session_token = authorization.replace("Bearer", "").strip()
            return await self._call_leave_group(session_token, body)
        

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