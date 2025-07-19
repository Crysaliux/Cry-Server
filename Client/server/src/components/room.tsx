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