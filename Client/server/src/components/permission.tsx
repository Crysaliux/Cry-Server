export interface Permission {
    group_id: string;
    role_id: string
    room_id: string | null;
    body: object;
    id: string;
}