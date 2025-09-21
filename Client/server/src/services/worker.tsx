import { Group, Message, PermissionsTable, Role, Room, Space, Member } from "components/index"
import { create } from "zustand";
import { useShallow } from 'zustand/react/shallow'

export interface Identifiable {
  id: string;
}

type ObjectRecord<T extends Identifiable> = Record<string, T>;

interface ObjectsActionState {
    groups: ObjectRecord<Group>;
    messages: ObjectRecord<Message>;
    permissions_table: PermissionsTable | null;
    roles: ObjectRecord<Role>;
    rooms: ObjectRecord<Room>;
    spaces: ObjectRecord<Space>;
    members: ObjectRecord<Member>;
    setObjects: <T extends Identifiable>(
        key: keyof ObjectsActionState,
        incoming: ObjectRecord<T>
    ) => void;
    setPermissionsTable: (table: PermissionsTable) => void;
}

export const useObjects = create<ObjectsActionState>((set) => ({
    groups: {},
    messages: {},
    permissions_table: null,
    roles: {},
    rooms: {},
    spaces: {},
    members: {},

    setObjects: (key, incoming) =>
        set((state) => {
            const current = state[key] as ObjectRecord<any>;
            const merged: ObjectRecord<any> = {};

            for (const id in incoming) {
                merged[id] = current[id]
                    ? { ...current[id], ...incoming[id] } //Merge operation
                    : incoming[id]; //New objects being added here.
            }
            
            return { [key]: merged } as Partial<ObjectsActionState>;
        }),

    setPermissionsTable: (table) =>
        set(() => ({
            permissions_table: table,
        })),
}));

export const useGroups = () => useObjects(useShallow((state) => Object.values(state.groups)));
export const useMessages = () => useObjects(useShallow((state) => Object.values(state.messages)));
export const usePermissionsTable = () => useObjects(useShallow((state) => state.permissions_table));
export const useRoles = () => useObjects(useShallow((state) => Object.values(state.roles)));
export const useRooms = () => useObjects(useShallow((state) => Object.values(state.rooms)));
export const useSpaces = () => useObjects(useShallow((state) => Object.values(state.spaces)));
export const useMembers = () => useObjects(useShallow((state) => Object.values(state.members)));