"""
The permgate module is initialized on the core startup. It parses the requested permissions and resolves their
child permissions, allowing the client to perform the operation.

The RDServer, later referred to as "the cache", is a Redis-backed server which stores the client
permissions for faster retrieval.

If the requested data isn't present in the cache, a fallback operation is triggered: the worker queries the database
through the session instance and fetches the missing data for future use.

v0.0.1 beta
"""


from ..worker import Client, Group, Space, Room, Message, Role, GlobalPermission, RoleToRoomPermission
from sqlalchemy import insert, select, update, delete, exists, and_, or_
from sqlalchemy.orm import selectinload
from collections import defaultdict
from typing import Literal
from functools import partial
import json
import os
import uuid


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "permgate_config.json")) as conf:
    PERMGATE_CONFIG = {key: value for key, value in json.load(conf).items() if not key.startswith("_")}


class Permgate:
    def __init__(self, rdserver_cache):
        self.rdserver_cache = rdserver_cache
        self.global_permissions = PERMGATE_CONFIG["GLOBAL_PERMISSIONS"]
        self.rtr_permissions = PERMGATE_CONFIG["ROLE_TO_ROOM_PERMISSIONS"]
        self.global_all = {}
        self.rtr_all = {}
        self.global_lookup = {}
        self.rtr_lookup = {}

        for key, parent in self.global_permissions.items():
            self.global_all[key] = [parent["name"]] + [self.global_permissions[child]["name"] for child in parent["children"]]

        for key, parent in self.rtr_permissions.items():
            self.rtr_all[key] = [parent["name"]] + [self.rtr_permissions[child]["name"] for child in parent["children"]]

        for key, item in self.global_permissions.items():
            self.global_lookup[item["name"]] = key

        for key, item in self.rtr_permissions.items():
            self.rtr_lookup[item["name"]] = key

        self.checks = {
            "must_have": self.__must_have,
            "any_of": self.__any_of,
        }

    def __fetch_children(self, perms: list[str], _all: dict[str, list[str]], lookup: dict[str, str]) -> list[str]:
        try:
            actual = []

            for perm in perms:
                if not perm in actual:
                    actual += _all[lookup[perm]]

            return True, actual
        except KeyError:
            return False, []
        
    def __must_have(self, perms: list[str], actual: list[str]):
        return set(perms).issubset(set(actual))
    
    def __any_of(self, perms: list[str], actual: list[str]):
        return set(perms) & set(actual)
    
    def __global_index(self, client_id: str, group_id: str):
        return f"client:{client_id}:group:{group_id}"
    
    def __rtr_index(self, client_id: str, room_id: str):
        return f"client:{client_id}:room:{room_id}"
    
    """
    CACHING DATA
    """

    async def __cache_global_all(self, client_id: str, global_perms: list[tuple[str]]):
        global_struct = defaultdict(list) #returns status, error
        for group_id, perm in global_perms:
            global_struct[group_id].append(perm)

        async with self.rdserver_cache.pipeline(transaction=False) as pipe:
            for group_id, perms in global_struct.items():
                await pipe.set(self.__global_index(client_id, group_id), perms) 
            result = await pipe.execute() #does it return a boolelan?

        if not result:
            return False, "..."
        
        return True, None
    
    async def __cache_global(self, client_id: str, group_id: str, global_perms: list[str]):
        result = await self.rdserver_cache.set(
            self.__global_index(client_id, group_id), 
            global_perms,
        ) #does it return a boolean?

        if not result:
            return False, "..."
        
        return True, None
    
    async def __cache_rtr_all(self, client_id: str, rtr_perms: list[tuple[str]]):
        rtr_struct = defaultdict(list) #returns status, error
        for room_id, perm in rtr_perms:
            rtr_struct[room_id].append(perm)

        async with self.rdserver_cache.pipeline(transaction=False) as pipe:
            for room_id, perms in rtr_struct.items():
                await pipe.set(self.__global_index(client_id, room_id), perms) 
            result = await pipe.execute() #does it return a boolelan?

        if not result:
            return False, "..."
        
        return True, None
    
    async def __cache_rtr(self, client_id: str, room_id: str, rtr_perms: list[str]):
        result = await self.rdserver_cache.set(
            self.__rtr_index(client_id, room_id), 
            rtr_perms,
        ) #does it return a boolean?

        if not result:
            return False, "..."
        
        return True, None
    
    """
    FETCHING DATA
    """

    async def prefetch_global_all(self, client_id: str, session):
        global_perms_res = await session.scalars(
            select(Group.id, GlobalPermission.name)
            .join(Group.members)
            .join(Client.roles)
            .join(Role.global_permissions)
            .where(Client.id == client_id).distinct()
        )
        global_perms = global_perms_res.all()
        
        status, error = await self.__cache_global_all(client_id, global_perms)

        if not status:
            return False, error
        
        return True, None
    
    """
    fetch_global fetches permissions for the given group. Passes if cached.
    """
    
    async def fetch_global(self, client_id: str, group_id: str, session): #status, error
        if await self.rdserver_cache.get(self.__global_index(client_id, group_id)):
            return True, None

        global_perms_res = await session.scalars(
            select(GlobalPermission.name)
            .join(Group.members)
            .join(Client.roles)
            .join(Role.global_permissions)
            .where(and_(
                Client.id == client_id,
                Group.id == group_id,
            )).distinct()
        )
        global_perms = global_perms_res.all()

        rtr_perms_res = await session.execute(
            select(Room.id, RoleToRoomPermission.name)
            .join(Client.roles)
            .join(Role.role_to_room_permissions)
            .where(Client.id == client_id).distinct()
        )
        rtr_perms = rtr_perms_res.all()
        
        status, error = await self.__cache_global(client_id, group_id, global_perms)
        if not status:
            return False, error
        
        status, error = await self.__cache_rtr_all(client_id, rtr_perms)
        if not status:
            return False, error
        
        return True, None
    
    """
    fetch_rtr fetches permissions for the given room. Passes if cached.
    """
    
    async def fetch_rtr(self, client_id: str, room_id: str, session):
        if await self.rdserver_cache.get(self.__rtr_index(client_id, room_id)):
            return True, None

        rtr_perms_res = await session.execute(
            select(RoleToRoomPermission.name)
            .join(Client.roles)
            .join(Role.role_to_room_permissions)
            .where(and_(
                Client.id == client_id,
                RoleToRoomPermission.room_id == room_id,
            )).distinct()
        )
        rtr_perms = rtr_perms_res.all()

        status, error = await self.__cache_rtr(client_id, room_id, rtr_perms)

        if not status:
            return False, error
        
        return True, None
    

    async def check_global(
            self, 
            client_id: str, 
            group_id: str, 
            check: Literal["must_have", "any_of"], 
            session
        ):
        perms = await self.rdserver_cache.get(self.__rtr_index(client_id, group_id))
        if not perms:
            perms_res = await session.scalars(
                select(GlobalPermission.name)
                .join(Client.groups)
                .join(Client.roles)
                .join(Role.global_permissions)
                .where(and_(
                    Client.id == client_id,
                    Group.id == group_id,
                ))
                .distinct()
            )
            perms = perms_res.all()

            status, error = await self.__cache_global(client_id, group_id, perms)
            if not status:
                return False, error

        if not perms:
            return False, "..."
        
        status, actual = self.__fetch_children(perms, self.global_all, self.global_lookup)
        if not status:
            return False, "..."
            
        return self.checks[check](perms, actual), None
    

    async def check_rtr(
            self, 
            client_id: str, 
            room_id: str, 
            check: Literal["must_have", "any_of"], 
            session
        ):
        perms = await self.rdserver_cache.get(self.__rtr_index(client_id, room_id))
        if not perms:
            perms_res = await session.scalars(
                select(RoleToRoomPermission.name)
                .join(Client.roles)
                .join(Role.role_to_room_permissions)
                .where(and_(
                    Client.id == client_id,
                    RoleToRoomPermission.room_id == room_id,
                )).distinct()
            )
            perms = perms_res.all()

            status, error = await self.__cache_rtr(client_id, room_id, perms)
            if not status:
                return False, error

        if not perms:
            return False, "..."
        
        status, actual = self.__fetch_children(perms, self.rtr_all, self.rtr_lookup)
        if not status:
            return False, "..."
            
        return self.checks[check](perms, actual), None


    async def evaluator(self, vld: dict[partial]):
        if callable(vld):
            return await vld()

        operation, children = vld

        if operation == "and":
            for child in children:
                status, error = await self.evaluator(child)
                if not status:
                    return False, error
            return True

        if operation == "or":
            for child in children:
                status, _ = await self.evaluator(child)
                if status:
                    return True, None
            return False

        raise ValueError(f"Invalid operation: {operation}")

    """
    ASSIGNING PERMISSIONS
    """

    async def assign_global(role_id: str, perms: list[str], session):
        query = insert(GlobalPermission).values(
            [
                {
                    "role_id": role_id,
                    "name": perm.name,
                    "id": str(uuid.uuid4()),
                } 
            for perm in perms])
        query = query.prefix_with("IGNORE")

        await session.execute(query)
        await session.commit()

    async def remove_global(role_id: str, perms: list[str], session):
        await session.execute(delete(GlobalPermission).where(and_(
            GlobalPermission.role_id == role_id,
            GlobalPermission.permission_name.in_(perms)
        )))
        await session.commit()

    """
    ADDING/REMOVING PERMISSIONS
    """

    async def add_global(role_id: str, perms: list[str], session):
        query = insert(GlobalPermission).values(
            [
                {
                    "role_id": role_id,
                    "name": perm.name,
                    "id": str(uuid.uuid4()),
                } 
            for perm in perms])
        query = query.prefix_with("IGNORE")

        await session.execute(query)
        await session.commit()


    async def remove_global(role_id: str, perms: list[str], session):
        await session.execute(delete(GlobalPermission).where(and_(
            GlobalPermission.role_id == role_id,
            GlobalPermission.name.in_(perms),
        )))
        await session.commit()


    async def add_rtr(role_id: str, room_id: str, perms: list[str], session):
        query = insert(RoleToRoomPermission).values(
            [
                {
                    "room_id": room_id,
                    "role_id": role_id,
                    "name": perm.name,
                    "id": str(uuid.uuid4()),
                } 
            for perm in perms])
        query = query.prefix_with("IGNORE")

        await session.execute(query)
        await session.commit()


    async def remove_rtr(role_id: str, room_id: str, perms: list[str], session):
        await session.execute(delete(RoleToRoomPermission).where(and_(
            RoleToRoomPermission.role_id == role_id,
            RoleToRoomPermission.room_id == room_id,
            RoleToRoomPermission.name.in_(perms),
        )))
        await session.commit()