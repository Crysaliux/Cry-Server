import { Group, Message, Permission, Role, Room, Space } from "components/index"
import { create } from "zustand";
import { GroupUpdateBody, MessageUpdateBody, RoleUpdateBody, RoomUpdateBody, SpaceUpdateBody } from "components/index";

interface ObjectsActionState {
    groups: { [id: string]: Group };
    messages: { [id: string]: Message };
    permissions: { [id: string]: Permission };
    roles: { [id: string]: Role };
    rooms: { [id: string]: Room };
    spaces: { [id: string]: Space };

    addGroup: (group: Group) => void;
    addMessage: (message: Message) => void;
    addPermission: (permission: Permission) => void;
    addRole: (role: Role) => void;
    addRoom: (room: Room) => void;
    addSpace: (space: Space) => void;

    updateGroup: (group_params: GroupUpdateBody) => void;
    updateMessage: (message_params: MessageUpdateBody) => void;
    updateRole: (role_params: RoleUpdateBody) => void;
    updateRoom: (room_params: RoomUpdateBody) => void;
    updateSpace: (space_params: SpaceUpdateBody) => void;

    deleteGroup: (id: string) => void;
    deleteMessage: (id: string) => void;
    deletePermission: (id: string) => void;
    deleteRole: (id: string) => void;
    deleteRoom: (id: string) => void;
    deleteSpace: (id: string) => void;
}

interface HeartbeatActionState {
    heartbeat_interval: number | null;
    setHeartbeatInterval: (interval: number | null) => void;
}

export const useObjects = create<ObjectsActionState>((set) => ({
    groups: {},
    messages: {},
    permissions: {},
    roles: {},
    rooms: {},
    spaces: {},
    
    addGroup: (group) => set((state) => ({ groups: { ...state.groups, [group.id]: group } })),
    addMessage: (message) => set((state) => ({ messages: { ...state.messages, [message.id]: message } })),
    addPermission: (permission) => set((state) => ({ permissions: { ...state.permissions, [permission.id]: permission } })),
    addRole: (role) => set((state) => ({ roles: { ...state.roles, [role.id]: role } })),
    addRoom: (room) => set((state) => ({ rooms: { ...state.rooms, [room.id]: room } })),
    addSpace: (space) => set((state) => ({ spaces: { ...state.spaces, [space.id]: space } })),


    updateGroup: (params) => set((state) => ({
      groups: {
        ...state.groups,
        [params.id]: { ...state.groups[params.id], ...params },
      },
    })),
    updateMessage: (params) => set((state) => ({
      messages: {
        ...state.messages,
        [params.id]: { ...state.messages[params.id], ...params },
      },
    })),
    updateRole: (params) => set((state) => ({
      roles: {
        ...state.roles,
        [params.id]: { ...state.roles[params.id], ...params },
      },
    })),
    updateRoom: (params) => set((state) => ({
      rooms: {
        ...state.rooms,
        [params.id]: { ...state.rooms[params.id], ...params },
      },
    })),
    updateSpace: (params) => set((state) => ({
      spaces: {
        ...state.spaces,
        [params.id]: { ...state.spaces[params.id], ...params },
      },
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

export const useHeartbeat = create<HeartbeatActionState>((set) => ({
    heartbeat_interval: null,
    setHeartbeatInterval: (interval) => set({ heartbeat_interval: interval }),
}));