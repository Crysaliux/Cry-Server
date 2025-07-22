export interface Permission {
    type: "permission";
    group_id: string;
    role_id: string
    room_id: string | null;
    body: object;
    id: string;
}

export interface PermissionNewBody {
    group_id: string;
    role_id: string;
    room_id: string;
    body: object;
    id: string;
}