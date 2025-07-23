export interface Role {
    type: "role";
    group_id: string;
    name: string;
    color: string;
    id: string;
}

export interface RoleNewBody {
    group_id: string;
    name: string;
    id: string;
}

export interface RoleUpdateBody {
    name: string;
    color: string;
    id: string;
}

export interface RoleDeleteBody {
    id: string;
}