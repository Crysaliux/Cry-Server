from ..worker import Client, Group, Space, Room, Message, Role, GlobalPermission, RoleToRoomPermission
from sqlalchemy import insert, select, update, delete, exists
from sqlalchemy.orm import selectinload
from typing import Literal
import json
import os
import uuid


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "permgate_config.json")) as conf:
    PERMGATE_CONFIG = {key: value for key, value in json.load(conf).items() if not key.startswith("_")}


class Permgate:
    def __init__(self):
        self.global_permissions = PERMGATE_CONFIG["GLOBAL_PERMISSIONS"]
        self.rtr_permissions = PERMGATE_CONFIG["ROLE_TO_ROOM_PERMISSIONS"]
        self.global_all = {}
        self.rtr_all = {}
        self.global_lookup = {}
        self.rtr_lookup = {}

        for key, parent in self.global_permissions.items():
            self.global_all[key] = [parent["name"]] + [self.global_permissions[child]["name"] for child in parent["children"]]

        for key, parent in self.role_to_room_permissions.items():
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
    

    async def check_global(
            self, 
            group_id: str, 
            client_id: str, 
            perms: list[str], 
            check: Literal["must_have", "any_of"], 
            session
        ):
        permissions_res = await session.scalars(
            select(GlobalPermission.name)
            .join(Client.groups)
            .join(Client.roles)
            .join(Role.global_permissions)
            .where(
                Client.id == client_id,
                Group.id == group_id,
            )
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
        permissions_res = await session.scalars(
            select(RoleToRoomPermission.name)
            .join(Client.roles)
            .join(Role.role_to_room_permissions)
            .where(
                Client.id == client_id,
                RoleToRoomPermission.room_id == room_id,
            )
            .distinct()
        )
        permissions = permissions_res.all()

        status, actual = self.__fetch_children(permissions, self.global_all, self.global_lookup)
        if not status:
            return False
        
        return self.checks[check](perms, actual)
    

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
        await session.execute(delete(GlobalPermission).where(
            GlobalPermission.role_id == role_id,
            GlobalPermission.permission_name.in_(perms)
        ))
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
        await session.execute(delete(RoleToRoomPermission).where(
            RoleToRoomPermission.role_id == role_id,
            RoleToRoomPermission.room_id == room_id,
            RoleToRoomPermission.permission_name.in_(perms)
        ))
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