export interface Room {
    type: "room";
    group_id: string;
    space_id: string;
    creator_id: string;
    name: string;
    about_room: string | null;
    nsfw: boolean;
    id: string;
}

export interface RoomNewBody {
    group_id: string;
    space_id: string;
    creator_id: string;
    name: string;
    about_room: string | null;
    id: string;
}

export interface RoomUpdateBody {
    name: string;
    about_room: string;
    nsfw: boolean;
    id: string;
}

export interface RoomDeleteBody {
    id: string;
}