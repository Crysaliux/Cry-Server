export interface Message {
    type: "message";
    group_id: string;
    space_id: string;
    room_id: string;
    author_id: string;
    content: string;
    id: string;
}