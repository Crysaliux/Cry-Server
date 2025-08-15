import { Group, Message, Permission, Role, Room, Space } from "components/index"
import { create } from "zustand";

export interface Identifiable {
  id: string;
}

type ObjectRecord<T extends Identifiable> = Record<string, T>;

interface ObjectsActionState {
    groups: ObjectRecord<Group>;
    messages: ObjectRecord<Message>;
    permissions: ObjectRecord<Permission>;
    roles: ObjectRecord<Role>;
    rooms: ObjectRecord<Room>;
    spaces: ObjectRecord<Space>;
    setObjects: <T extends Identifiable>(
        key: keyof ObjectsActionState,
        incoming: ObjectRecord<T>
    ) => void;
}

export const useObjects = create<ObjectsActionState>((set) => ({
    groups: {},
    messages: {},
    permissions: {},
    roles: {},
    rooms: {},
    spaces: {},

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
        })
}));

export const useGroups = () => useObjects((state) => Object.values(state.groups));
export const useMessages = () => useObjects((state) => Object.values(state.messages));
export const usePermissions = () => useObjects((state) => Object.values(state.permissions));
export const useRoles = () => useObjects((state) => Object.values(state.roles));
export const useRooms = () => useObjects((state) => Object.values(state.rooms));
export const useSpaces = () => useObjects((state) => Object.values(state.spaces));