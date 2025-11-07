from fastapi import FastAPI, Request, Form, WebSocket, HTTPException, Depends, WebSocketDisconnect, WebSocketException, APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse, Response
from pydantic import BaseModel, TypeAdapter, Field as _type, ValidationError
from typing import TypeAlias, Literal
from ..services.worker import Client, Group, Space, Room, Message, Role, RoleToRoomPerms
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import insert, select, update, delete, exists
from sqlalchemy.orm import selectinload
from ast import literal_eval
from datetime import datetime, timedelta, timezone
from ..components import *
from .validators import *
from PIL import Image
from functools import wraps
import aiofiles
from socketio.async_server import AsyncServer
from typing import Union
import asyncio
import uuid
import jwt


#Emission types
EmitError: TypeAlias = None
EmitCommon: TypeAlias = None


class GatewayModel(BaseModel):
    body: Union[
        UpdateClient,
        CreateGroup,
        UpdateGroup,
        DeleteGroup,
        SendMessage,
        EditMessage,
        DeleteMessage,
        CreateRole,
        UpdateRole,
        DeleteRole,
        CreateRoom,
        UpdateRoom,
        DeleteRoom,
        CreateSpace,
        UpdateSpace,
        DeleteSpace,
        CreatePermissionsTable,
        UpdatePermissionsTable,
        #DeletePermissionsTable, not implemented yet.
        JoinGroup,
    ]


class Listener: #Add objectifiers!
    def __init__(
            self, 
            hasher, 
            session,  
            ws,
            logger,
            oauth2,
            cecchm,
            storage_images_path: str, 
            storage_files_path: str, 
            max_message_length: dict, 
            max_image_size: int, 
            max_file_size: dict, 
            client_server_origin: str, 
            algorithm, access_key, 
            addr: tuple, 
            gateway: AsyncServer,
            perms,
        ):
        self.addr = addr
        self.access_key = access_key
        self.hasher = hasher
        self.session = session
        self.ws = ws
        self.logger = logger
        self.oauth2 = oauth2
        self.cecchm = cecchm
        self.storage_images_path = storage_images_path
        self.storage_files_path = storage_files_path
        self.max_message_length = max_message_length
        self.max_image_size = max_image_size
        self.max_file_size = max_file_size
        self.client_server_origin = client_server_origin
        self.algorithm = algorithm
        self.gateway = gateway
        self.perms = perms

        self.event_bindings = {
            "connect": self.__on_connect,
            "disconnect": self.__on_disconnect,

            "create_group": self.__on_create_group,
            "create_space": self.__on_create_space,
            "create_room": self.__on_create_room,
            "send_message": self.__on_send_message,
            "create_role": self.__on_create_role,
            "create_permissions_table": self.__on_create_permissions_table,

            "update_client": self.__on_update_client,
            "update_group": self.__on_update_group,
            "update_space": self.__on_update_space,
            "update_room": self.__on_update_room,
            "edit_message": self.__on_edit_message,
            "update_role": self.__on_update_role,
            "update_permissions_table": self.__on_update_permissions_table,

            "delete_client": self.__on_delete_client,
            "delete_group": self.__on_delete_group,
            "delete_space": self.__on_delete_space,
            "delete_room": self.__on_delete_room,
            "delete_message": self.__on_delete_message,
            "delete_role": self.__on_delete_role,
            "delete_permissions_table": ..., # why? Idk

            "join_group": self.__on_join_group,
            "join_room": self.__on_join_room,
            
            "leave_room": self.__on_leave_room,
            "leave_group": self.__on_leave_group,
        }
        self.__register_event_handlers()

    def __register_event_handlers(self) -> None:
        for event, handler in self.event_bindings.items():
            self.gateway.on(event, self.ws(handler, self.session))

    def __verify_request(self, data: dict) -> tuple[bool, GatewayModel | None]:
        try:
            model_data = GatewayModel(**data)
            return True, model_data
        except ValidationError:
            return False, None
        

    async def __emit_error(self, sid, event: str, error: dict) -> EmitError:
        await self.gateway.emit(event, {
            "status": False,
            "body": None,
            "error": error,
        }, to=sid)

#Listener module's main body
    async def __on_connect(self, sid, eviron, auth, session) -> Literal[False] | EmitCommon:
        try: access_token = auth["access_token"]
        except KeyError:
            return False
        
        valid = ClientValidator(self.access_key, self.algorithm)
        status, client = await valid.access_token_is_valid(access_token, session)

        if not status:
            return False
        
        await self.gateway.save_session(sid, {"client": client, "access_token": access_token})
        join_status = await self.cecchm.join_groups(sid, client.groups)
        if not join_status:
            await self.__emit_error(sid, "on_connect_operation", {"index": "CLUSTER_JOIN_FAILED", "target": "groups"})

    async def __on_disconnect(self, sid, session):
        ...

    #ON_CREATE...
    async def __on_create_group(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "group_created", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "group_created", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "group_created", {"index": "WRONG_REQUEST", "target": "group"})
            return

        body = data.body
        name, global_name, about_group, icon_url, id = body.name, body.global_name, body.about_group, body.icon_url, str(uuid.uuid4())

        extra_client_res = await session.execute(select(Client).options(
            selectinload(Client.groups),
        ).where(Client.id == client.id))
        extra_client = extra_client_res.scalar_one_or_none()

        global_name_check_res = await session.execute(select(Group).where(Group.global_name == global_name))
        global_name_check = global_name_check_res.scalar_one_or_none()

        if global_name_check:
            await self.__emit_error(sid, "group_created", {"index": "GLOBAL_NAME_EXISTS", "target": "group"})
            return

        new_group = Group(owner_id=client.id, name=name, global_name=global_name, about_group=about_group, icon_url=icon_url, id=id)
        new_room = Room(
            group_id=id, 
            space_id=None, 
            creator_id=client.id, 
            name="mega room", 
            about_room="You can rename me, but can't delete me. Unless you got plenty of other rooms!", #make it a variable
            id=str(uuid.uuid4()),
        )
        
        session.add(new_group)
        session.add(new_room)
        extra_client.groups.append(new_group)
        await session.commit()

        await self.gateway.emit("group_created", {
            "status": True,
            "body": {"id": id},
            "error": None,
        }, to=sid)

    async def __on_create_space(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "space_created", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "space_created", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "space_created", {"index": "WRONG_REQUEST", "target": "space"})
            return

        body = data.body
        group_id, name, id = body.group_id, body.name, str(uuid.uuid4())

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "space_created", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "space_created", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_SPACES"]):
            session.add(Space(group_id=group_id, creator_id=client.id, name=name, id=id)) 
            await session.commit()
            
            await self.gateway.emit("space_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, "space_created", {"index": "MISSING_PERMISSION", "target": "MANAGE_SPACES"})

    async def __on_create_room(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "room_created", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "room_created", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "room_created", {"index": "WRONG_REQUEST", "target": "room"})
            return

        body = data.body
        group_id, space_id, name, about_room, id = body.group_id, body.space_id, body.name, body.about_room, str(uuid.uuid4())

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "room_created", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "room_created", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROOMS"]):
            new_room = Room(group_id=group_id, space_id=space_id, creator_id=client.id, name=name, about_room=about_room, id=id)
            session.add(new_room)
            await session.commit()

            await self.gateway.emit("room_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, "room_created", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROOMS"})

    async def __on_send_message(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "message_sent", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "message_sent", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "message_sent", {"index": "WRONG_REQUEST", "target": "message"})
            return

        body = data.body
        group_id, room_id, content, id = body.group_id, body.room_id, body.content, str(uuid.uuid4())

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "message_sent", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "message_sent", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)

        if perm_valid.global_validity(["CO_OWNER", "SEND_MESSAGES"]) or \
        perm_valid.has_room_permissions_all(room_id, ["SEND_MESSAGES"]):
            session.add(Message(group_id=group_id, room_id=room_id, author_id=client.id, content=content, id=id)) 
            await session.commit()

            await asyncio.gather(
                self.gateway.emit("message_sent", {
                    "status": True, 
                    "body": {
                        "client_id": client.id,
                        "nickname": client.nickname, 
                        "content": content, 
                        "id": id
                    }, 
                    "error": None
                }, room=f"#{room_id}"),

                self.gateway.emit("message_sent_notif", {
                    "group_id": group_id,
                    "room_id": room_id, 
                    "nickname": client.nickname,
                    "content": content,
                }, room=f"${group_id}"),
            )
        else:
            await self.__emit_error(sid, "message_sent", {"index": "MISSING_PERMISSION", "target": "SEND_MESSAGES"})
    
    async def __on_create_role(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "role_created", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "role_created", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "role_created", {"index": "WRONG_REQUEST", "target": "role"})
            return

        body = data.body
        group_id, name, id = body.group_id, body.name, str(uuid.uuid4())

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "role_created", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "role_created", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROLES"]):
            session.add(Role(group_id=group_id, name=name, id=id))
            await session.commit()
            await self.gateway.emit("role_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, "role_created", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROLES"})

    async def __on_create_permissions_table(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "permissions_table_created", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "permissions_table_created", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "permissions_table_created", {"index": "WRONG_REQUEST", "target": "permissions_table"})
            return

        body = data.body
        group_id, role_id, room_id, permissions, id = body.group_id, body.role_id, body.room_id, body.permissions, str(uuid.uuid4())

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "permissions_table_created", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "permissions_table_created", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROLES"]):
            session.add(RoleToRoomPerms(group_id=group_id, role_id=role_id, room_id=room_id, permissions=perm_valid.mask_room_permissions(permissions), id=id))
            await session.commit()
            await self.gateway.emit("permissions_table_created", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, room=f"${group_id}")
        else:
            await self.__emit_error(sid, "permissions_table_created", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROLES"})

    #ON_UPDATE_...
    async def __on_update_client(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "client_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "client_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "client_updated", {"index": "WRONG_REQUEST", "target": "client"})
            return

        body = data.body
        username, nickname, about_me, avatar_url, color_theme = body.username, body.nickname, body.about_me, body.avatr_url, body.color_theme

        username_check_res = await session.execute(select(Client).where(Client.username == username))
        username_check = username_check_res.scalar_one_or_none()

        if username_check:
            await self.__emit_error(sid, "client_updated", {"index": "USERNAME_EXISTS", "target": "client"})
            return

        update_status_res = await session.execute(update(Client).where(Client.id == client.id).values(username=username, nickname=nickname, about_me=about_me, avatar_url=avatar_url, color_theme=color_theme).returning(Client.id))
        update_status = update_status_res.scalar_one_or_none()
        if update_status:
            client_updated_res = await session.execute(select(Client).options(
                selectinload(Client.groups),
            ).where(Client.id == client.id))
            client_updated = client_updated_res.scalar_one_or_none()

            if not client_updated:
                await self.__emit_error(sid, "client_updated", {"index": "UPDATE_FAILED", "target": "client"})
                return
            
            await self.gateway.save_session(sid, {"client": client_updated})

            emits = [
                self.gateway.emit("client_updated", {
                    "status": True, 
                    "body": {
                        "username": username,
                        "nickname": nickname, 
                        "avatar_url": avatar_url, 
                        "id": client.id,
                    },
                    "error": None,
                }, room=f"${group.id}")
                for group in client.groups
            ]
            emits.append(
                self.gateway.emit("client_updated", {
                    "status": True, 
                    "body": {"id": client.id},
                    "error": None,
                }, room=sid)
            )
            await asyncio.gather(*emits)
        else:
            await self.__emit_error(sid, "client_updated", {"index": "UPDATE_FAILED", "target": "client"})

    async def __on_update_group(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "group_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "group_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "group_updated", {"index": "WRONG_REQUEST", "target": "group"})
            return

        body = data.body
        name, global_name, about_group, icon_url, nsfw, content_filter, content_filter_level, id = body.owner_id, body.name, body.global_name, body.about_group, body.icon_url, body.nsfw, body.content_filter, body.content_filter_level, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "group_updated", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "group_updated", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_GROUP"]):
            update_status_res = await session.execute(update(Group).where(Group.id == id).values(name=name, global_name=global_name, about_group=about_group, icon_url=icon_url, nsfw=nsfw, content_filter=content_filter, content_filter_level=content_filter_level).returning(Group.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("group_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${id}")
            else:
                await self.__emit_error(sid, "group_updated", {"index": "UPDATE_FAILED", "target": "group"})
        else:
            await self.__emit_error(sid, "group_updated", {"index": "MISSING_PERMISSION", "target": "MANAGE_GROUP"})
    
    async def __on_update_space(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "space_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "space_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "space_updated", {"index": "WRONG_REQUEST", "target": "space"})
            return

        body = data.body
        group_id, name, id = body.group_id, body.creator_id, body.name, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "space_updated", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "space_updated", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_SPACES"]):
            update_status_res = await session.execute(update(Space).where(Space.id == id).values(name=name).returning(Space.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("space_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, "space_updated", {"index": "UPDATE_FAILED", "target": "space"})
        else:
            await self.__emit_error(sid, "space_updated", {"index": "MISSING_PERMISSION", "target": "MANAGE_SPACES"})
    
    async def __on_update_room(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "room_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "room_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "room_updated", {"index": "WRONG_REQUEST", "target": "room"})
            return

        body = data.body
        group_id, space_id, name, about_room, nsfw, id = body.group_id, body.space_id, body.creator_id, body.name, body.about_room, body.nsfw, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "room_updated", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "room_updated", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROOMS"]):
            update_status_res = await session.execute(update(Room).where(Room.id == id).values(space_id=space_id, name=name, about_room=about_room, nsfw=nsfw).returning(Room.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("room_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, "room_updated", {"index": "UPDATE_FAILED", "target": "room"})
        else:
            await self.__emit_error(sid, "room_updated", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROOMS"})
    
    async def __on_edit_message(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "message_edited", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "message_edited", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "message_edited", {"index": "WRONG_REQUEST", "target": "message"})
            return

        body = data.body
        group_id, room_id, content, id = body.group_id, body.space_id, body.room_id, body.content, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        message_res = await session.execute(select(Message).options(
            selectinload(Message.author),
        ).where(Message.id == id, Message.group_id == group_id))
        message = message_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "message_edited", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "message_edited", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        if not message:
            await self.__emit_error(sid, "message_edited", {"index": "OBJECT_NON_EXISTANT", "target": "message"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_MESSAGES"]) or \
        perm_valid.has_room_permissions_all(room_id, ["MANAGE_MESSAGES"]) or \
        message.author.id == client.id:
            update_status_res = await session.execute(update(Message).where(Message.id == id).values(content=content).returning(Message.id))
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("message_edited", {
                    "status": True, 
                    "body": {
                        "content": content,
                        "id": id,
                    }, 
                    "error": None
                }, room=f"#{room_id}")
            else:
                await self.__emit_error(sid, "message_edited", {"index": "UPDATE_FAILED", "target": "message"})
        else:
            await self.__emit_error(sid, "message_edited", {"index": "MISSING_PERMISSION", "target": "MANAGE_MESSAGES"})

    async def __on_update_role(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "role_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "role_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "role_updated", {"index": "WRONG_REQUEST", "target": "role"})
            return

        body = data.body
        group_id, name, color, global_permissions, id = body.group_id, body.name, body.color, body.global_permissions, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "role_updated", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "role_updated", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROLES"]):
            update_status_res = await session.execute(
                update(Role).where(Role.id == id, Role.group_id == group_id).values(
                    name=name, 
                    color=color, 
                    global_permissions=perm_valid.mask_global_permissions(global_permissions), 
                ).returning(Role.id)
            )
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("role_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, "role_updated", {"index": "UPDATE_FAILED", "target": "role"})
        else:
            await self.__emit_error(sid, "role_updated", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROLES"})

    async def __on_update_permissions_table(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "permissions_table_updated", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "permissions_table_updated", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "permissions_table_updated", {"index": "WRONG_REQUEST", "target": "role"})
            return

        body = data.body
        group_id, permissions, id = body.group_id, body.permissions, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "permissions_table_updated", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "permissions_table_updated", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROLES"]):
            update_status_res = await session.execute(
                update(RoleToRoomPerms).where(RoleToRoomPerms.id == id, RoleToRoomPerms.group_id == group_id).values(
                    permissions=perm_valid.mask_room_permissions(permissions)
                ).returning(RoleToRoomPerms.id)
            )
            update_status = update_status_res.scalar_one_or_none()
            if update_status:
                await self.gateway.emit("permissions_table_updated", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, "permissions_table_updated", {"index": "UPDATE_FAILED", "target": "permissions_table"})
        else:
            await self.__emit_error(sid, "permissions_table_updated", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROLES"})
    
    #ON_DELETE
    async def __on_delete_client(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "client_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "client_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return
         
        deletion_status_res = await session.execute(delete(Client).where(Client.id == client.id))
        deletion_status = deletion_status_res.scalar_one_or_none()
        if deletion_status:
            await self.gateway.emit("client_deleted", {
                "status": True, 
                "body": {"id": client.id}, 
                "error": None
            }, to=sid)
            await self.gateway.disconnect(sid)
        else:
            await self.__emit_error(sid, "client_deleted", {"index": "DELETION_FAILED", "target": "client"})
    
    async def __on_delete_group(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "group_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "group_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "group_deleted", {"index": "WRONG_REQUEST", "target": "group"})
            return

        body = data.body
        id = body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.members),
        ).where(Group.id == id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "group_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "group_deleted", {"index": "UNRELATED", "target": "client<->group"})
            return

        if group.owner.id == client.id:
            deletion_status_res = await session.execute(delete(Group).where(Group.id == id).returning(Group.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("group_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${id}")
            else:
                await self.__emit_error(sid, "group_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
        else:
            await self.__emit_error(sid, "group_deleted", {"index": "DELETION_REJECTED", "target": "group"})

    async def __on_delete_space(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "space_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "space_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "space_deleted", {"index": "WRONG_REQUEST", "target": "space"})
            return

        body = data.body
        group_id, id = body.group_id, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "space_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "space_deleted", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)

        if perm_valid.global_validity(["CO_OWNER", "MANAGE_SPACES"]):
            deletion_status_res = await session.execute(delete(Space).where(Space.id == id).returning(Space.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("space_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, "space_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "space"})
        else:
            await self.__emit_error(sid, "space_deleted", {"index": "MISSING_PERMISSION", "target": "MANAGE_SPACES"})
    
    async def __on_delete_room(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "room_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "room_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "room_deleted", {"index": "WRONG_REQUEST", "target": "room"})
            return

        body = data.body
        group_id, id = body.group_id, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "room_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "room_deleted", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROOMS"]):
            deletion_status_res = await session.execute(delete(Room).where(Room.id == id).returning(Room.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("room_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, "room_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "room"})
        else:
            await self.__emit_error(sid, "room_deleted", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROOMS"})
    
    async def __on_delete_message(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "message_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "message_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "message_deleted", {"index": "WRONG_REQUEST", "target": "message"})
            return

        body = data.body
        group_id, room_id, id = body.group_id, body.room_id, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        message_res = await session.execute(select(Message).where(Message.id == id))
        message = message_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "message_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "message_deleted", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        if not message:
            await self.__emit_error(sid, "message_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "message"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_MESSAGES"]) or \
        perm_valid.has_room_permissions_all(room_id, ["MANAGE_MESSAGES"]) or \
        client.id == message.author_id:
            deletion_status_res = await session.execute(delete(Message).where(Message.id == id).returning(Message.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("message_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${room_id}")
            else:
                await self.__emit_error(sid, "message_deleted", {"index": "DELETION_FAILED", "target": "message"})
        else:
            await self.__emit_error(sid, "message_deleted", {"index": "MISSING_PERMISSION", "target": "MANAGE_MESSAGES"})
    
    async def __on_delete_role(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "role_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "role_deleted", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "role_deleted", {"index": "WRONG_REQUEST", "target": "role"})
            return

        body = data.body
        group_id, id = body.group_id, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "role_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "role_deleted", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)
        
        if perm_valid.global_validity(["CO_OWNER", "MANAGE_ROLES"]):
            deletion_status_res = await session.execute(delete(Role).where(Role.id == id).returning(Role.id))
            deletion_status = deletion_status_res.scalar_one_or_none()
            if deletion_status:
                await self.gateway.emit("role_deleted", {
                    "status": True, 
                    "body": {"id": id}, 
                    "error": None
                }, room=f"${group_id}")
            else:
                await self.__emit_error(sid, "role_deleted", {"index": "OBJECT_NON_EXISTANT", "target": "role"})
        else:
            await self.__emit_error(sid, "role_deleted", {"index": "MISSING_PERMISSION", "target": "MANAGE_ROLES"})

    #ON_JOIN
    async def __on_join_group(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "group_joined", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "group_joined", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "group_joined", {"index": "WRONG_REQUEST", "target": "group"})
            return

        body = data.body
        global_name = body.global_name

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members), #Members needed?
        ).where(Group.global_name == global_name))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "group_joined", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "group_joined", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms) #WHAT IF BANNED/KICKED?
        
        join_status = await self.cecchm.join_group(sid, id)
        if not join_status:
            await self.__emit_error(sid, "group_joined", {"index": "CLUSTER_JOIN_FAILED", "target": "group"})
            
        await self.gateway.emit("group_joined", {
            "status": True, 
            "body": {"id": id}, 
            "error": None
        }, to=sid)

    async def __on_join_room(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "room_joined", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "room_joined", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "room_joined", {"index": "WRONG_REQUEST", "target": "room"})
            return

        body = data.body
        group_id, id = body.group_id, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        room_res = await session.execute(select(Room).where(Room.id == id))
        room = room_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "room_joined", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return

        if not room:
            await self.__emit_error(sid, "room_joined", {"index": "OBJECT_NON_EXISTANT", "target": "room"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "room_joined", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)
        
        if perm_valid.global_validity(["CO_OWNER"]) or \
        perm_valid.has_room_permissions_all(id, ["VIEW_ROOM"]):
            join_status = await self.cecchm.join_room(sid, id)
            if not join_status:
                await self.__emit_error(sid, "room_joined", {"index": "CLUSTER_JOIN_FAILED", "target": "room"})
            await self.gateway.emit("room_joined", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, to=sid)
        else:
            await self.__emit_error(sid, "room_joined", {"index": "MISSING_PERMISSION", "target": "VIEW_ROOM"})

    async def __on_leave_group(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "group_left", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "group_left", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "group_left", {"index": "WRONG_REQUEST", "target": "room"})
            return

        body = data.body
        id = body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == id))
        group = group_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "group_left", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "group_left", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)
        
        if not perm_valid.global_validity(["CO_OWNER"]):
            leave_status = await self.cecchm.leave_group(sid, id)
            if not leave_status:
                await self.__emit_error(sid, "group_left", {"index": "CLUSTER_LEAVE_FAILED", "target": "group"})
            
            group.members.remove(client_check)
            await session.commit()
            
            await self.gateway.emit("group_left", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, to=sid)
        else:
            await self.__emit_error(sid, "room_left", {"index": "IS_AN_OWNER", "target": "group"}) #Add to errors!

    #ON_LEAVE
    async def __on_leave_room(self, sid, data, session) -> EmitCommon:
        client_session = await self.gateway.get_session(sid)
        client, access_token = client_session["client"], client_session["access_token"]

        if not client:
            await self.__emit_error(sid, "room_left", {"index": "OBJECT_NON_EXISTANT", "target": "client"})
            return
        
        valid = ClientValidator(self.access_key, self.algorithm)
        if not await valid.running_session_is_valid(access_token):
            await self.__emit_error(sid, "room_left", {"index": "INVALID_OR_EXPIRED_SESSION_TOKEN", "target": "client"})
            return

        status, data = self.__verify_request(data)
        if not status:
            await self.__emit_error(sid, "room_left", {"index": "WRONG_REQUEST", "target": "room"})
            return

        body = data.body
        group_id, id = body.group_id, body.id

        group_res = await session.execute(select(Group).options(
            selectinload(Group.roles),
            selectinload(Group.members),
        ).where(Group.id == group_id))
        group = group_res.scalar_one_or_none()

        room_res = await session.execute(select(Room).where(Room.id == id))
        room = room_res.scalar_one_or_none()

        if not group:
            await self.__emit_error(sid, "room_left", {"index": "OBJECT_NON_EXISTANT", "target": "group"})
            return

        if not room:
            await self.__emit_error(sid, "room_left", {"index": "OBJECT_NON_EXISTANT", "target": "room"})
            return
        
        client_chec_res = await session.execute(select(Client).where(Client.id == client.id))
        client_check = client_chec_res.scalar_one_or_none()
        if not client_check in group.members:
            await self.__emit_error(sid, "room_left", {"index": "UNRELATED", "target": "client<->group"})
            return
        
        perm_valid = PermissionValidator(client, group, self.perms)
        
        if perm_valid.global_validity(["CO_OWNER"]) or \
        perm_valid.has_room_permissions_all(id, ["VIEW_ROOM"]): #are they neccessary?
            join_status = await self.cecchm.join_room(sid, id)
            if not join_status:
                await self.__emit_error(sid, "room_left", {"index": "CLUSTER_JOIN_FAILED", "target": "room"})
            await self.gateway.emit("room_left", {
                "status": True, 
                "body": {"id": id}, 
                "error": None
            }, to=sid)
        else:
            await self.__emit_error(sid, "room_left", {"index": "MISSING_PERMISSION", "target": "VIEW_ROOM"})