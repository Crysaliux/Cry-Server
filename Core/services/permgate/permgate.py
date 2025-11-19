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
            "one_of": self.__one_of,
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
    
    def __one_of(self, perms: list[str], actual: list[str]):
        return set(perms) & set(actual)

#Redis = System God, Worker = System God's accountant.
#loading, validation
    async def load_all(self, client_id: str, group_id: str, session):
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
        await self.rdserver_cache.set(f"client:{client_id}:global", global_perms)

        rtr_perms_res = await session.execute(
            select(Room.id, RoleToRoomPermission.name)
            .join(Role.role_to_room_permissions)
            .join(Client.roles)
            .join(Room.group)
            .where(Client.id == client_id).distinct()
        )
        rtr_perms = rtr_perms_res.all()

        rtr_struct = defaultdict(list)
        for room_id, perm in rtr_perms:
            rtr_struct[room_id].append(perm)

        for room_id, perms in rtr_struct:
            await self.rdserver_cache.set(f"client:{client_id}:room:{room_id}", perms)

    """
    async def check_owner(self, group_id: str, client_id: str, session):
        owner_group_rel_exists = await session.execute(select(exists().where(and_(
            Group.id == group_id,
            Group.owner_id == client_id,
        )))).scalar()
        if not owner_group_rel_exists:
            return False
        return True
    
    async def check_author(self, message_id: str, client_id: str, session):
        author_message_rel_exists = await session.execute(select(exists().where(and_(
            Message.id == message_id,
            Message.author_id == client_id,
        )))).scalar()
        if not author_message_rel_exists:
            return False
        return True
    
    async def check_global(
            self, 
            group_id: str, 
            client_id: str, 
            perms: list[str], 
            check: Literal["must_have", "any_of"], 
            session
        ):   
        if not perms:
            return False

        permissions_res = await session.scalars(
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
        permissions = permissions_res.all()

        status, actual = self.__fetch_children(permissions, self.global_all, self.global_lookup)
        if not status:
            return False
            
        return self.checks[check](perms, actual)
    
    async def check_rtr(
            self, 
            client_id: str, 
            room_id: str, 
            perms: list[str], 
            check: Literal["must_have", "any_of"], 
            session
        ):    
        if not perms:
            return False

        permissions_res = await session.scalars(
            select(RoleToRoomPermission.name)
            .join(Client.roles)
            .join(Role.role_to_room_permissions)
            .where(and_(
                Client.id == client_id,
                RoleToRoomPermission.room_id == room_id,
            ))
            .distinct()
        )
        permissions = permissions_res.all()

        status, actual = self.__fetch_children(permissions, self.global_all, self.global_lookup)
        if not status:
            return False
        
        return self.checks[check](perms, actual)
    
    async def evaluator(self, vld: dict[partial]):
        if callable(vld):
            return await vld()

        operation, children = vld

        if operation == "and":
            for child in children:
                if not await self.evaluator(child):
                    return False
            return True

        if operation == "or":
            for child in children:
                if await self.evaluator(child):
                    return True
            return False

        raise ValueError(f"Invalid operation: {operation}")
    

    async def fetch_accessable(self, client_id: str, group_id: str, session):
        rooms_res = await session.scalars(
            select(Room.name)
            .join(Room.role_to_room_permissions)
            .join(RoleToRoomPermission.role)
            .join(Role.assignees)
            .join(Client.groups)
            .where(and_(
                Client.id == client_id,
                Group.id == group_id,
                RoleToRoomPermission.name == "VIEW_ROOM"
        )))
        rooms = rooms_res.all()
        return rooms
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

    
    async def assign_rtr(role_id: str, room_id: str, perms: list[str], session):
        query = insert(GlobalPermission).values(
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
            RoleToRoomPermission.permission_name.in_(perms),
        )))
        await session.commit()

"""
role = session.query(Role).filter_by(name="moderator").one()
channel = session.query(Channel).filter_by(name="general").one()

link = RoleToRoomPermission(
    role=role,
    channel=channel,
    can_send_message=True, 
    can_pin_message=True
)
session.add(link)
session.commit()

for link in role.channel_links:
    print(link.channel.name, link.can_send_message, link.can_pin_message)


FOR SPEED:

session.add_all([Permission(name=n) for n in names])
session.commit() !!!
"""