export interface FriendRequest {
    type: 'friend_request';
    id: number | string;
    client_id: number | string;
    client_name: string;
}