import { z } from "zod";

export interface PermissionsTable{
    group_id: string;
    permissions: string[];
    id: string;
}

export const PermissionsTableSchema = z.object({
    group_id: z.string(),
    permissions: z.array(z.string()),
    id: z.string(),
});