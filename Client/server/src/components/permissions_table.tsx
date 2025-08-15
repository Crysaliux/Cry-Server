import { z } from "zod";

export interface PermissionsTable{
    permissions: string[];
    id: string;
}

export const PermissionsTableSchema = z.object({
    permissions: z.array(z.string()),
    id: z.string(),
});