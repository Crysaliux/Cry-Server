import { z } from "zod";

export interface Member {
    nickname: string;
    id: string;
}

export const MemberSchema = z.object({
    nickname: z.string(),
    id: z.string(),
});