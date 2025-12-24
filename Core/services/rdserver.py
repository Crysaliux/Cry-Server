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
from .worker import Client, Group, Space, Room, Message, Role
from redis.asyncio import Redis, ConnectionError, RedisError
from pydantic import BaseModel, ValidationError
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

    async def group_(self, group_id: str):
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

            if not members:
                return False, None, "306"

            banned_res = await self.session.execute(
                select(Client.id)
                .join(Group.banned)
                .where(Group.id == group_id)
            )
            banned = banned_res.all()
            
            model = RedisDataModel(**{
                "members": members,
                "banned": banned,
            })
            group = model

            status, error = await self.rdserver.set_(f"group:{group_id}", model)
            if not status:
                return False, None, error
            
        return True, group, None


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