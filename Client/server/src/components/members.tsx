export interface Member {
    type: 'member';
    id: number | string;
    name: string;
    icon_path: string;
    status: string;
}

export interface ToRemoveMember {
    type: 'member_remove';
    id: number | string;
}