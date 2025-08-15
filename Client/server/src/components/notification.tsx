import { z } from "zod";

export interface Notification {
    group_id: string;
    room_id: string;
    nickname: string;
    content: string;
}

export const NotificationSchema = z.object({
    group_id: z.string(),
    room_id: z.string(),
    nickname: z.string(),
    content: z.string(),
});