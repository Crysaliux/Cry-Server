export interface Room {
    group_id: string;
    space_id: string | null;
    name: string;
    about_room: string | null;
    nsfw: boolean;
    id: string;
}