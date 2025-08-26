import { z } from "zod";

export interface Message {
    author_id: string;
    nickname: string;
    content: string;
    sent_at: string;
    id: string;
}

export const MessageSchema = z.object({
    author_id: z.string(),
    nickname: z.string(),
    content: z.string(),
    sent_at: z.string(),
    id: z.string(),
});