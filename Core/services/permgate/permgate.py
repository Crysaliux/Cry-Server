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
from ..rdserver import Fallback
from sqlalchemy.orm import selectinload
from collections import defaultdict
import numpy as np
from typing import Literal
from functools import partial
import asyncio
from asyncio import Semaphore
import json
import os
import uuid


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "permgate_config.json")) as conf:
    PERMGATE_CONFIG = {key: value for key, value in json.load(conf).items() if not key.startswith("_")}


class Permgate:
    def __init__(self, rdserver):
        self.rdserver = rdserver
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
    FETCH ON LOAD
    """

    def __to_dict(self, perms: list[tuple[str]]):
        struct = defaultdict(list)
        for parent, perm in perms:
            struct[parent].append(perm)
        return dict(struct)

    async def fetch_on_load(self, client_id: str, session):
        status, client, error = await self.rdserver.get_(f"client:{client_id}")
        if not status:
            return False, error
        if not client:
            return False, "305"
        
        global_perms_res = await session.scalars(
            select(Group.id, GlobalPermission.name)
            .join(Group.members)
            .join(Client.roles)
            .join(Role.global_permissions)
            .where(Client.id == client_id).distinct()
        )
        global_perms = global_perms_res.all()
        
        rtr_perms_res = await session.scalars(
            select(Group.id, GlobalPermission.name)
            .join(Group.members)
            .join(Client.roles)
            .join(Role.global_permissions)
            .where(Client.id == client_id).distinct()
        )
        rtr_perms = rtr_perms_res.all()

        if global_perms:
            rtg_rel = self.__to_dict(global_perms)
            status, error = self.rdserver.set_(f"client:{client_id}", {
                "groups": rtg_rel,
            })

            if not status:
                return False, error
            
        if rtr_perms:
            rtr_rel = self.__to_dict(rtr_perms)
            status, error = self.rdserver.set_(f"client:{client_id}", {
                "rooms": rtr_rel,
            })

            if not status:
                return False, error
        
        return True, None
    

    async def check_global(
            self, 
            client_id: str, 
            group_id: str, 
            perms: list[str],
            check: Literal["must_have", "any_of"], 
        ):
        
        status, client, error = await self.rdserver.get_(f"client:{client_id}")
        if not status:
            return False, False, error
        if not client:
            return False, False, "305"
        
        status, actual = self.__fetch_children(client.groups[group_id], self.global_all, self.global_lookup)
        if not status:
            return False, "..."
            
        return True, self.checks[check](perms, actual), None
    
    async def check_rtr(
            self, 
            client_id: str, 
            room_id: str, 
            perms: list[str],
            check: Literal["must_have", "any_of"], 
        ):
        
        status, client, error = await self.rdserver.get_(f"client:{client_id}")
        if not status:
            return False, False, error
        if not client:
            return False, False, "305"
        
        status, actual = self.__fetch_children(client.rooms[room_id], self.rtr_all, self.rtr_lookup)
        if not status:
            return False, "..."
            
        return True, self.checks[check](perms, actual), None
    
    async def check_author(
            self, 
            client_id: str, 
            message_id: str,
            session
        ):
            
        is_author = await session.execute(
            select(exists().where(and_(
                Message.id == message_id,
                Message.author_id == client_id
            )))
        ).scalar()

        return is_author


    async def evaluator(self, vld: dict[partial]):
        if callable(vld):
            return await vld()

        operation, children = vld

        if operation == "and":
            for child in children:
                status, allowed, error = await self.evaluator(child)
                if not status:
                    return False, False, error
                if not allowed:
                    return True, True, None
            return True

        if operation == "or":
            for child in children:
                status, allowed, error = await self.evaluator(child)
                if not status:
                    return False, False, error
                if allowed:
                    return True, True, None
            return False

        raise ValueError(f"Invalid operation: {operation}")

    """
    ADDING/REMOVING PERMISSIONS
    """
    async def __batch_update_worker(
            self, 
            semaphore: Semaphore, 
            clients_batch: list[str], 
            perms: list[str],
            operation: Literal["add", "remove"],
            target: Literal["global", "rtr"],
            target_id: str,
            role_id: str
        ):
        async with semaphore:
            status, error = await self.rdserver.perms_bulk_update_(
                clients_batch,
                perms,
                operation,
                target,
                target_id,
                role_id
            )
            return status, error

    async def __perms_batch_update(
            self, 
            clients: list[str],
            perms: list[str],
            operation: Literal["add", "remove"],
            target: Literal["global", "rtr"],
            target_id: str,
            role_id: str
        ):
        clients = np.array(clients)
        semaphore  = Semaphore(20) #make adjustable later
        tasks = [
            self.__batch_update_worker(
                semaphore, 
                batch, 
                perms,
                operation,
                target,
                target_id,
                role_id
            ) for batch in np.array_split(clients, len(clients) // 100) #make adjustable later
        ]
        result = await asyncio.gather(*tasks)
        for resp in result:
            status, error = resp #It's unlikely to have more than 1000 concurrent tasks, aka 100000 members per group
            if not status:
                return False, error
        return True, None
    
    async def __batch_cleanup_worker(
            self, 
            semaphore: Semaphore, 
            clients_batch: list[str], 
            group_id: str,
            rooms: list[str]
        ):
        async with semaphore:
            status, error = await self.rdserver.perms_bulk_cleanup_(
                clients_batch,
                group_id,
                rooms
            )
            return status, error

    async def __perms_batch_cleanup(
            self, 
            clients: list[str],
            group_id: str,
            rooms: list[str]
        ):
        clients = np.array(clients)
        semaphore  = Semaphore(20) #make adjustable later
        tasks = [
            self.__batch_cleanup_worker(
                semaphore, 
                batch, 
                group_id,
                rooms
            ) for batch in np.array_split(clients, len(clients) // 100) #make adjustable later
        ]
        result = await asyncio.gather(*tasks)
        for resp in result:
            status, error = resp #It's unlikely to have more than 1000 concurrent tasks, aka 100000 members per group
            if not status:
                return False, error
        return True, None


    async def add_global(self, group_id: str, role_id: str, perms: list[str], session):
        fallback = Fallback()
        status, group, error = await fallback.group_(group_id)
        if not status:
            return False, error
        
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
        
        status, error = await self.__perms_batch_update(
            group.members,
            perms,
            "add",
            "global",
            group_id,
            role_id,
        )
        if not status:
            return False, error
        return True, None
  
    async def remove_global(self, group_id: str, role_id: str, perms: list[str], session):
        fallback = Fallback()
        status, group, error = await fallback.group_(group_id)
        if not status:
            return False, error
        
        result = await session.execute(delete(GlobalPermission).where(and_(
            GlobalPermission.role_id == role_id,
            GlobalPermission.name.in_(perms),
        )))
        await session.commit()

        if result.rowcount() == 0:
            return False, "320"
        
        status, error = await self.__perms_batch_update(
            group.members,
            perms,
            "remove",
            "global",
            group_id,
            role_id
        )
        if not status:
            return False, error
        return True, None


    async def add_rtr(self, group_id: str, role_id: str, room_id: str, perms: list[str], session):
        fallback = Fallback()
        status, group, error = await fallback.group_(group_id)
        if not status:
            return False, error
        
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
        
        status, error = await self.__perms_batch_update(
            group.members,
            perms,
            "add",
            "rtr",
            room_id,
            role_id
        )
        if not status:
            return False, error
        return True, None

    async def remove_rtr(self, group_id: str, role_id: str, room_id: str, perms: list[str], session):
        fallback = Fallback()
        status, group, error = await fallback.group_(group_id)
        if not status:
            return False, error
        
        result = await session.execute(delete(RoleToRoomPermission).where(and_(
            RoleToRoomPermission.role_id == role_id,
            RoleToRoomPermission.room_id == room_id,
            RoleToRoomPermission.name.in_(perms),
        )))
        await session.commit()
        
        if result.rowcount() == 0:
            return False, "319"
        
        status, error = await self.__perms_batch_update(
            group.members,
            perms,
            "remove",
            "rtr",
            room_id,
            role_id
        )
        if not status:
            return False, error
        return True, None


    async def cleanup(self, group_id: str, session):
        fallback = Fallback()
        status, group, error = await fallback.group_(group_id)
        if not status:
            return False, error
        
        rooms_res = await session.scalars(
            select(Room.id)
            .join(Group.rooms)
            .where(Group.id == group_id)
        )
        rooms = rooms_res.all()

        result = await session.execute(delete(Group).where(Group.id == group_id))
        await session.commit()
        
        if result.rowcount() == 0:
            return False, "306"
        
        status, error = await self.__perms_batch_cleanup(
            group.members,
            group_id,
            rooms
        )
        if not status:
            return False, error
        
        status, error = await self.rdserver.delete_(f"group:{group_id}")
        if not status:
            return False, error
        return True, None