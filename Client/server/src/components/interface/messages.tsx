export interface Message {
    type: 'message';
    id: number;
    sender_id: number;
    group_id: number;
    channel_id: number;
    sender_name: string;
    sender_icon_path: string;
    content: string;
    unread: boolean;
}

//ServerRequests

export interface ToRemoveMessage {
    type: 'message_remove';
    id: number;
}

export interface MessageCreationStatus {
    type: 'message_creation_status';
    status: boolean;
    error: string | null;
}

/*
Updates are handled automatically when client receives partial representation of an initial interface (Message)
*/