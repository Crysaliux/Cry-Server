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

    def __fetch_children(self, perms: list[str], _all: dict[str, list[str]], lookup: dict[str, str]) -> list[str]:
        try:
            perms_set = set(perms)
            actual = []

            for perm in perms_set:
                if not perm in actual:
                    actual += _all[lookup[perm]]

            return True, actual
        except KeyError:
            return False, []
        
    async def is_permitted(self, client_id: str, session, must_have: list[str] | None = None, one_of: list[str] | None = None):
        if must_have:


            status, actual = self.__fetch_children()