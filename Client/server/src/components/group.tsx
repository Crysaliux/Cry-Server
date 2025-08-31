import { z } from "zod";

export interface Group {
    name: string;
    about_group: string | null;
    icon_url: string | null;
    nsfw: boolean;
    id: string;

    content_filter: boolean;
    content_filter_level: string;
}

export const GroupSchema = z.object({
    name: z.string(),
    about_group: z.string().nullable(),
    icon_url: z.string().nullable(),
    nsfw: z.boolean(),
    id: z.string(),

    content_filter: z.boolean(),
    content_filter_level: z.string(),
});