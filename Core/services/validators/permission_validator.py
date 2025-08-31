from ..worker import Client, Group

class PermissionValidator:
    def __init__(self, client: Client, group: Group):
        self.client = client
        self.group = group

    def mask_global_permissions(self, names: list[str]) -> int:
        permissions = 0
        for name in names:
            permissions |= getattr(self.perms._global, name, 0)
        return permissions
    
    def mask_room_permissions(self, names: list[str]) -> int:
        permissions = 0
        for name in names:
            permissions |= getattr(self.perms._room_oriented, name, 0)
        return permissions
    
    def unmask_global_permissions(self, mask: int) -> list[str]:
        res = []
        for name, value in vars(self.perms._room_oriented).items():
            if name.startswith("__"): #skipping __module__ instances
                continue
            if mask & value:
                res.append(name)
        return res
    
    def unmask_room_permissions(self, mask: int) -> list[str]:
        #Not implemented
        raise NotImplementedError

    def has_global_permissions_all(self, names: list[str]) -> bool:
        masked = self.mask_global_permissions(names)
        for role in self.group.roles:
            if self.client not in role.assignees:
                continue
            if (role.global_permissions & masked) == masked:
                return True
        return False
    
    def has_global_permissions_any(self, names: list[str]) -> bool:
        masked = self.mask_global_permissions(names)
        for role in self.group.roles:
            if self.client not in role.assignees:
                continue
            if role.global_permissions & masked:
                return True
        return False

    def has_room_permissions_all(self, room_id: int, names: list[str]) -> bool:
        masked = self.mask_room_permissions(names)
        for role in self.group.roles:
            if self.client not in role.assignees:
                continue
            for perm_table in role.role_to_room_perm_tables:
                if perm_table.room_id != room_id:
                    continue
                if (perm_table.permissions & masked) == masked:
                    return True
        return False
    
    def has_room_permissions_any(self, room_id: int, names: list[str]) -> bool:
        masked = self.mask_room_permissions(names)
        for role in self.group.roles:
            if self.client not in role.assignees:
                continue
            for perm_table in role.role_to_room_perm_tables:
                if perm_table.room_id != room_id:
                    continue
                if perm_table.permissions & masked:
                    return True
        return False
    
    def global_validity(self, names: list[str]) -> bool:
        if self.client.id == self.group.owner.id or \
        self.has_global_permissions_any(names):
            return True
        return False