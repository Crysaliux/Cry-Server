export interface Member {
    type: 'member';
    id: number | string;
    name: string;
    icon_path: string;
    status: string;
}

//ServerRequests

export interface ToRemoveMember {
    type: 'member_remove';
    id: number | string;
}

/*
Updates are handled automatically when client receives partial representation of an initial interface (Member)
*/