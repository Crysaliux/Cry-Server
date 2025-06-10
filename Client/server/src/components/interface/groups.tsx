import { Member } from "./members";

export interface Group {
    type: 'group';
    id: number;
    owner_id: number;
    icon_path: string;
    name: string;
    desc: string;
}

//ServerRequests

export interface ToRemoveGroup {
    type: 'group_remove';
    id: number;
}

export interface ToLoadGroupMembers {
    type: 'group_load_members';
    id: number;
    members: Member[];
}

//ClientRequests

export interface ToRequestGroupMembers {
    type: 'group_request_members';
    id: number;
}

/*
Updates are handled automatically when client receives partial representation of an initial interface (Group)
*/