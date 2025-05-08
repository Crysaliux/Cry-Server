import { Member } from "./members";

export interface Group {
    type: 'group';
    id: number | string;
    owner_id: number | string;
    icon_path: string;
    name: string;
    desc: string;
}

//ServerRequests

export interface ToRemoveGroup {
    type: 'group_remove';
    id: number | string;
}

export interface ToLoadGroupMembers {
    type: 'group_load_members';
    id: number | string;
    members: Member[];
}

//ClientRequests

export interface ToRequestGroupMembers {
    type: 'group_request_members';
    id: number | string;
}

/*
Updates are handled automatically when client receives partial representation of an initial interface (Group)
*/