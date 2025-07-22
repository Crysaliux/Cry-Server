export interface Group {
    type: "group";
    owner_id: string;
    name: string;
    about_group: string | null;
    icon_url: string | null;
    nsfw: boolean;
    id: string;

    content_filter: boolean;
    content_filter_level: string;
}

export interface GroupNewBody {
    owner_id: string;
    name: string;
    about_group: string | null;
    icon_url: string;
    id: string;
}

export interface GroupUpdateBody {
    name: string;
    about_group: string | null;
    icon_url: string;
    nsfw: boolean;
    id: string;

    content_filter: boolean;
    content_filterlevel: string;
}