export interface Group {
    type: "group";
    owner_id: string;
    name: string;
    about_group: string | null;
    icon_url: string | null;
    nsfw: boolean;
    id: string;
}