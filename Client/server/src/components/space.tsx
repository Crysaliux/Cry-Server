import { z } from "zod";

export interface Space {
    group_id: string;
    name: string;
    id: string;
}

export const SpaceSchema = z.object({
    group_id: z.string(),
    name: z.string(),
    id: z.string(),
});