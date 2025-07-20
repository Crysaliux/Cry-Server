import { Group, Message, Permission, Role, Room, Space } from "components/index"
import { create } from "zustand";

interface ActionState {
    groups: { [id: string]: Group };
    messages: { [id: string]: Message };
    permissions: { [id: string]: Permission };
    roles: { [id: string]: Role };
    rooms: { [id: string]: Room };
    spaces: { [id: string]: Space };

    setGroup: (group: Group) => void;
    setMessage: (message: Message) => void;
    setPermission: (permission: Permission) => void;
    setRole: (role: Role) => void;
    setRoom: (room: Room) => void;
    setSpace: (space: Space) => void;

    deleteGroup: (id: string) => void;
    deleteMessage: (id: string) => void;
    deletePermission: (id: string) => void;
    deleteRole: (id: string) => void;
    deleteRoom: (id: string) => void;
    deleteSpace: (id: string) => void;
}

export const useWorker = create<ActionState>((set) => ({
    groups: {},
    messages: {},
    permissions: {},
    roles: {},
    rooms: {},
    spaces: {},
    
    setGroup: (group) => set((state) => ({
        groups: { ...state.groups, [group.id]: state.groups[group.id] ? { ...state.groups[group.id], ...group } : group },
    })),
    setMessage: (message) => set((state) => ({
        messages: { ...state.messages, [message.id]: state.messages[message.id] ? { ...state.messages[message.id], ...message } : message },
    })),
    setPermission: (permission) => set((state) => ({
        permissions: { ...state.permissions, [permission.id]: state.permissions[permission.id] ? { ...state.permissions[permission.id], ...permission } : permission },
    })),
    setRole: (role) => set((state) => ({
        roles: { ...state.roles, [role.id]: state.roles[role.id] ? { ...state.roles[role.id], ...role } : role },
    })),
    setRoom: (room) => set((state) => ({
        rooms: { ...state.rooms, [room.id]: state.rooms[room.id] ? { ...state.rooms[room.id], ...room } : room },
    })),
    setSpace: (space) => set((state) => ({
        spaces: { ...state.spaces, [space.id]: state.spaces[space.id] ? { ...state.spaces[space.id], ...space } : space },
    })),

    deleteGroup: (id) => set((state) => {
        const { [id]: _, ...rest } = state.groups;
        return { groups: rest };
    }),
    deleteMessage: (id) => set((state) => {
        const { [id]: _, ...rest } = state.messages;
        return { messages: rest };
    }),
    deletePermission: (id) => set((state) => {
        const { [id]: _, ...rest } = state.permissions;
        return { permissions: rest };
    }),
    deleteRole: (id) => set((state) => {
        const { [id]: _, ...rest } = state.roles;
        return { roles: rest };
    }),
    deleteRoom: (id) => set((state) => {
        const { [id]: _, ...rest } = state.rooms;
        return { rooms: rest };
    }),
    deleteSpace: (id) => set((state) => {
        const { [id]: _, ...rest } = state.spaces;
        return { spaces: rest };
    }),
}));