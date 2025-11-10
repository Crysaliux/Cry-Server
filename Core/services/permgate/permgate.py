from ..worker import Client, Group, Space, Room, Message, Role, GlobalPermission
from sqlalchemy import insert, select, update, delete, exists
from sqlalchemy.orm import selectinload
import json
import os


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "permgate_config.json")) as conf:
    PERMGATE_CONFIG = {key: value for key, value in json.load(conf).items() if not key.startswith("_")}


class Permgate:
    def __init__(self):
        self.global_permissions = PERMGATE_CONFIG["GLOBAL_PERMISSIONS"]
        self.role_to_room_permissions = PERMGATE_CONFIG["ROLE_TO_ROOM_PERMISSIONS"]
        self.global_all = {}
        self.role_to_room_all = {}
        self.global_lookup = {}
        self.role_to_room_lookup = {}

        for key, parent in self.global_permissions.items():
            self.global_all[key] = [parent["name"]] + [self.global_permissions[child]["name"] for child in parent["children"]]

        for key, parent in self.role_to_room_permissions.items():
            self.role_to_room_all[key] = [parent["name"]] + [self.role_to_room_permissions[child]["name"] for child in parent["children"]]

        for key, item in self.global_permissions.items():
            self.global_lookup[item["name"]] = key

        for key, item in self.role_to_room_permissions.items():
            self.role_to_room_lookup[item["name"]] = key

    def __fetch_children(self, perms: list[GlobalPermission], _all: dict[str, list[str]], lookup: dict[str, str]) -> list[str]:
        try:
            actual = []

            for perm in perms:
                if not perm.name in actual:
                    actual += _all[lookup[perm.name]]

            return True, actual
        except KeyError:
            return False, []
        
    async def global_must_have(self, client_id: str, perms: list[str], session):
        permissions_res = await session.scalars(
            select(GlobalPermission)
            .join(Role.global_permissions)
            .join(Client.roles)
            .where(Client.id == client_id)
            .distinct()
        )
        permissions = permissions_res.all()

        status, actual = self.__fetch_children(permissions, self.global_all, self.global_lookup)
        if not status:
            return False
            
        if not set(perms).issubset(set(actual)):
            return False
            
        return True

    async def global_one_of(self, client_id: str, perms: list[str], session): #Fix it, (One of!)
        permissions_res = await session.scalars(
            select(GlobalPermission)
            .join(Role.global_permissions)
            .join(Client.roles)
            .where(Client.id == client_id)
            .distinct()
        )
        permissions = permissions_res.all()

        status, actual = self.__fetch_children(permissions, self.global_all, self.global_lookup)
        if not status:
            return False
            
        if not set(perms).issubset(set(actual)):
            return False
            
        return True

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