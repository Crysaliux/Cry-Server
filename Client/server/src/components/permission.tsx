export interface Permission {
    type: "permission";
    group_id: string;
    role_id: string
    room_id: string | null;
    body: {};
    id: string;
}