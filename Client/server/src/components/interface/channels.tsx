export interface Channel {
    type: 'channel';
    id: number;
    creator_id: number;
    group_id: number;
    name: string;
}

//ServerRequests

export interface ToRemoveChannel {
    type: 'channel_remove';
    id: number;
}

/*
Updates are handled automatically when client receives partial representation of an initial interface (Channel)
*/