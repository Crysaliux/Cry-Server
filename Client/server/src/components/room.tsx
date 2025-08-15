import { z } from "zod";

export interface Room {
    group_id: string;
    space_id: string | null;
    name: string;
    about_room: string | null;
    nsfw: boolean;
    id: string;
}

export const RoomSchema = z.object({
    group_id: z.string(),
    space_id: z.string().nullable(),
    name: z.string(),
    about_room: z.string().nullable(),
    nsfw: z.boolean(),
    id: z.string(),
});