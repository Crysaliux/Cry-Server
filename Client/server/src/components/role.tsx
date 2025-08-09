export interface Role {
    group_id: string;
    name: string;
    color: string;
    id: string;

    global_permissions: [];
    room_oriented_permissions: [];
}