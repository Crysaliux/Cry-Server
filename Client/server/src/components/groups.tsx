export interface Group {
    type: 'group';
    id: number | string;
    owner_id: number | string;
    icon_path: string;
    name: string;
    desc: string;
}