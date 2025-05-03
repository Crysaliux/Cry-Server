export interface Message {
    type: 'message';
    id: number | string;
    sender_id: number | string;
    sender_name: string;
    sender_icon_path: string;
    content: string;
}