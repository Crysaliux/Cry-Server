import { z } from "zod";

export interface Client {
    username: string;
    nickname: string;
    about_me: string | null;
    avatar_url: string | null;
    color_theme: string | null;
    id: string;
}

export const ClientSchema = z.object({
    username: z.string(),
    nickname: z.string(),
    about_me: z.string().nullable(),
    avatar_url: z.string().nullable(),
    color_theme: z.string().nullable(),
    id:z.string(),
});