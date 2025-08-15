import { z } from "zod";

export interface Message {
    client_id: string;
    nickname: string;
    content: string;
    id: string;
}

export const MessageSchema = z.object({
    client_id: z.string(),
    nickname: z.string(),
    content: z.string(),
    id: z.string(),
});