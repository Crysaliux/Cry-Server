export interface Group {
    name: string;
    about_group: string | null;
    icon_url: string | null;
    nsfw: boolean;
    id: string;

    content_filter: boolean;
    content_filter_level: string;
}