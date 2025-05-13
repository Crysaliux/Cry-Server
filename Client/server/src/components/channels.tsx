export interface Channel {
    type: 'channel';
    id: number | string;
    creator_id: number | string;
    group_id: number | string;
    name: string;
}

//ServerRequests

export interface ToRemoveChannel {
    type: 'channel_remove';
    id: number | string;
}

export interface ChannelCreationStatus {
    type: 'channel_creation_status';
    status: boolean;
    error: string | null;
}

/*
Updates are handled automatically when client receives partial representation of an initial interface (Channel)
*/