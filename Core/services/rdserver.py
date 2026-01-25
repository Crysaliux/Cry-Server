"""
The rdmserver module handles redis database requests.

data = {
    "name": "Sillyrubber",
    "id": 1234,
}

redis_data_model = RedisData_model(**data)

v0.0.1 beta
"""

from sqlalchemy import insert, select, update, delete, exists, and_
from .worker import Client, Group, Space, Room, Message, Role, blocked_relationship
from redis.asyncio import Redis, ConnectionError, RedisError
from pydantic import BaseModel, ValidationError
from collections import defaultdict
from typing import Literal

class RedisDataModel(BaseModel):
    name: str
    details: dict

    @classmethod
    def from_redis(cls, json_string: str):
        return cls.model_validate_json(json_string)

    def to_redis(self) -> str:
        return self.model_dump_json()
    

class Fallback:
    def __init__(self, session, rdserver):
        self.session = session
        self.rdsserver = rdserver

    async def group_(self, id: str | None = None, global_name: str | None = None):
        group_id = id
        gb_name = global_name

        if not id:
            if not global_name:
                raise("No globalname provided")
            status, data, error = await self.rdserver.get_(f"globalname:{global_name}")
            if not status:
                return False, None, error
            if not data:
                gid_res = await self.session.execute(
                    select(Group.id)
                    .where(Group.global_name == global_name)
                )
                gid = gid_res.scalar_one_or_none()

                if not gid:
                    return False, None, "306"
                
                model = RedisDataModel(**{
                    "id": gid
                })

                status, error = await self.rdserver.set_(f"globalname:{global_name}", model)
                if not status:
                    return False, None, error
                group_id = gid

            if not group_id:
                group_id = data.id

        status, group, error = await self.rdserver.get_(f"group:{group_id}")
        if not status:
            return False, None, error
        if not group:
            members_res = await self.session.execute(
                select(Client.id)
                .join(Group.members)
                .where(Group.id == group_id)
            )
            members = members_res.all()
            
            rooms_res = await self.session.execute(
                select(Room.id)
                .join(Group.rooms)
                .where(Group.id == group_id)
            )
            rooms = rooms_res.all()

            if not members or not rooms:
                return False, None, "306"

            banned_res = await self.session.execute(
                select(Client.id)
                .join(Group.banned)
                .where(Group.id == group_id)
            )
            banned = banned_res.all()

            rest_res = await self.session.execute(
                select(
                    Group.name, 
                    Group.about_group, 
                    Group.icon_url, 
                    Group.nsfw, 
                    Group.content_filter,
                    Group.content_filter_level,
                )
                .where(Group.id == group_id)
            )
            rest = rest_res.scalar_one_or_none()

            if not gb_name:
                gb_name_res = await self.session.execute(
                    select(Group.global_name)
                    .where(Group.id == group_id)
                )
                gb_name = gb_name_res.scalar_one_or_none()
    
            model = RedisDataModel(**{
                "name": rest[0],
                "global_name": gb_name,
                "about_group": rest[1],
                "icon_url": rest[2],
                "nsfw": rest[3],
                "content_filter": rest[4],
                "content_filter_level": rest[5],

                "members": members,
                "rooms": rooms,
                "banned": banned,
            })
            group = model

            status, error = await self.rdserver.set_(f"group:{group_id}", model)
            if not status:
                return False, None, error
            
        return True, group, None
    
    async def client_(self, id: str, pg, refresh_token: str | None = None, check_token: bool = False):
        status, client, error = await self.rdserver.get_(f"client:{id}")
        if not status:
            return False, None, error
        if not client:
            rsh_token = refresh_token

            if check_token:
                fback_client_res = await self.session.execute(select(Client).where(
                    and_(
                        Client.id == id,
                        Client.refresh_token == refresh_token,
                    )
                ))
            else:
                fback_client_res = await self.session.execute(select(Client).where(Client.id == id))

            fback_client = fback_client_res.scalar_one_or_none()
            if not fback_client:
                return False, None, "305"
            
            if not rsh_token:
                rsh_token = fback_client.refresh_token

            blocked_res = (
                select(blocked_relationship.c.blocked_id)
                .where(blocked_relationship.c.client_id == client.id)
            )
            blocked = await self.session.scalars(blocked_res).all()
            
            model = RedisDataModel(**{
                "username": fback_client.username,
                "nickname": fback_client.nickname,
                "password": fback_client.password_hashed,
                "email": fback_client.email,
                "date_or_birth": fback_client.date_of_birth,
                "blocked": blocked,

                "refresh_token": rsh_token,
                "roles": {}, # "role_id": "group_id"
                "permissions": {
                    "groups": {}, # "group_id": [..]
                    "rooms": {},# "room_id": [...]
                },
                "sid": None,
                "id": id,
            })

            status, error = await self.rdserver.set_(f"client:{id}", model)
            if not status:
                return False, None, error
            
            #Fetching permissions related data (roles, permissions)
            status, error = await pg.fetch_on_load(client.id, self.session)
            if not status:
                return False, None, error
            
            return True, model, None
        
        if check_token:
            if client.refresh_token != refresh_token:
                return False, None, "317"
            return True, client, None
        
        return True, client, None
        

class RDServer:
    def __init__(self, host='localhost', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db
        self.r = None

    async def connect(self) -> tuple[bool, None, str | None]:
        try:
            self.r = Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
            await self.r.ping()
        except ConnectionError as e:
            self.r = None
            raise(e)
        
    """
    MAIN
    """

    async def set_(self, key: str, data_model: RedisDataModel) -> tuple[bool, None, str | None]:
        if not self.r: #Cannot set data: Not connected to Redis.
            return False, "200"
        try:
            await self.r.set(key, data_model.to_redis())
            return True, None
        except RedisError: #Redis error setting data for key '{key}': {e}
            return False, "201"

    async def get_(self, key: str) -> tuple[bool, RedisDataModel | None, str | None]:
        if not self.r:
            return False, None, "200"
        try:
            json_string = await self.r.get(key)
            if json_string:
                try:
                    return True, RedisDataModel.from_redis(json_string), None
                except ValidationError: #Pydantic validation error for key '{key}': {e}. Data might be corrupted or malformed
                    return False, None, "202"
            else:
                return True, None, None
        except RedisError: #Redis error getting data for key '{key}': {e}
            return False, None, "203"

    async def update_(self, key: str, new_data: dict) -> tuple[bool, str | None]:
        if not new_data: #"Update skipped: new_data dictionary is empty."
            return False, "204"

        if not self.r:
            return False, "200"

        status, existing_model, error = await self.get_(key)
        if not status:
            return False, error

        if existing_model:
            try:
                existing_model.details.update(new_data)
                set_status, _, error = await self.set_(key, existing_model)
                if set_status:
                    return True, None
                else: #Failed to save updated data for key '{key}': {set_error}
                    return False, error
            except Exception as e:
                return False, "205"
        else: #Cannot update. No existing data found for key '{key}'.
            return False, "206"
        
    async def delete_(self, key: str) -> tuple[bool, None, tuple[str, str] | None]: #status, error
        if not self.r:
            return False, "200"
        try:
            result = await self.r.delete(key)
            if result == 1:
                return True, None
            else:
                return False, "207"
        except RedisError:
            return False, "203"
        except Exception as e:
            return False, "208"
        
    """
    DEDICATED
    """

    async def perms_bulk_update_(
            self, 
            keys: list[str], 
            perms: list[str], 
            operation: Literal["add", "remove"],
            target: Literal["global", "rtr"],
            target_id: str,
            role_id: str,
        ) -> tuple[bool, str | None]:

        def op_add(model: RedisDataModel, data: list[str], target: Literal["global", "rtr"]):
            if target == "global":
                model.permissions.groups[target_id].extend(data)
            elif target == "rtr":
                model.permissions.rooms[target_id].extend(data)

        def op_remove(model: RedisDataModel, data: list[str], target: Literal["global", "rtr"]):
            if target == "global":
                initial = model.permissions.groups[target_id]
                model.permissions.groups[target_id] = [_ for _ in initial if _ not in data]
            elif target == "rtr":
                initial = model.permissions.rooms[target_id]
                model.permissions.rooms[target_id] = [_ for _ in initial if _ not in data]

        ops = {
            "add": op_add,
            "remove": op_remove,
        }

        if not perms: #"Update skipped: perms dictionary is empty."
            return False, "204"

        if not self.r:
            return False, "200"

        pipe = self.r.pipeline()
        for key in keys:
            pipe.get(key)
        fetched = await pipe.execute()

        pipe = self.r.pipeline()
        for key, obj in zip(keys, fetched):
            try:
                if obj:
                    model = RedisDataModel.from_redis(obj)
                    if role_id in model.roles.keys():
                        ops[operation](model, perms, target)
                        pipe.set(key, model.to_redis())
            except ValidationError: #Pydantic validation error for key '{key}': {e}. Data might be corrupted or malformed
                return False, "202"
            except Exception as e: #for later logging!
                return False, "205"
        result = await pipe.execute() #for later logging!

        return True, None
    
    async def perms_bulk_cleanup_(
            self, 
            keys: list[str], 
            group_id: str,
            rooms: list[str],
        ) -> tuple[bool, str | None]:

        if not self.r:
            return False, "200"

        pipe = self.r.pipeline()
        for key in keys:
            pipe.get(key)
        fetched = await pipe.execute()

        pipe = self.r.pipeline()
        for key, obj in zip(keys, fetched):
            try:
                if obj:
                    model = RedisDataModel.from_redis(obj)
                    rfound, gfound, rmfound = False, False, False
                    if group_id in model.roles.values():
                        roles_new = {key: value for key, value in model.roles.items() if value != group_id}
                        model.roles = roles_new
                        rfound = True
                    if group_id in model.groups.keys():
                        del model.groups[group_id]
                        gfound = True
                    if rooms in model.rooms.keys():
                        rooms_new = {key: value for key, value in model.rooms.items() if key not in rooms}
                        model.rooms = rooms_new
                        rmfound = True
                    if rfound or gfound or rmfound:
                        pipe.set(key, model.to_redis())
            except ValidationError: #Pydantic validation error for key '{key}': {e}. Data might be corrupted or malformed
                return False, "202"
            except Exception as e: #for later logging!
                return False, "205"
        result = await pipe.execute() #for later logging!

        return True, None