export interface Space {
    type: "space";
    group_id: string;
    creator_id: string;
    name: string;
    id: string;
}

export interface SpaceNewBody {
    group_id: string;
    creator_id: string;
    name: string;
    id: string;
}

export interface SpaceUpdateBody {
    name: string;
    id: string;
}

export interface SpaceDeleteBody {
    id: string;
}