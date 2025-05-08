export interface Message {
    type: 'message';
    id: number | string;
    sender_id: number | string;
    group_id: number | string;
    channel_id: number | string;
    sender_name: string;
    sender_icon_path: string;
    content: string;
    unread: boolean;
}

export interface ToRemoveMessage {
    type: 'message_remove';
    id: number | string;
}