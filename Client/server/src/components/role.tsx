import { z } from "zod";

export interface Role {
    group_id: string;
    name: string;
    color: string;
    global_permissions: string[];
    id: string;
}

export const RoleSchema = z.object({
    group_id: z.string(),
    name: z.string(),
    color: z.string(),
    global_permissions: z.array(z.string()),
    id: z.string(),
});