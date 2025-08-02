from ..worker import worker_session, Client, Group

class PermissionValidator:
    def __init__(self, client: Client, group: Group):
        self.client = client
        self.group = group

    def has_global_permission(self, perm_name: str) -> bool:
        for role in self.group.roles:
            if self.client not in role.assignees:
                continue
            for perm in role.permissions:
                if perm.body["global"] and perm.body["permission"] == perm_name:
                    return True
        return False

    def has_room_permission(self, perm_name: str, room_id: int) -> bool:
        for role in self.group.roles:
            if self.client not in role.assignees:
                continue
            for perm in role.permissions:
                if not perm.body["global"] \
                and perm.body["permission"] == perm_name \
                and getattr(perm.room, "id", None) == room_id:
                    return True
        return False