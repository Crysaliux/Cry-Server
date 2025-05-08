export interface Channel {
    type: 'channel';
    id: number | string;
    group_id: number | string;
    name: string;
}

export interface ToRemoveChannel {
    type: 'channel_remove';
    id: number | string;
}