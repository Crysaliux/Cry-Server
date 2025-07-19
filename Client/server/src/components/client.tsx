export interface Client {
    type: "client";
    nickname: string;
    about_me: string | null;
    avatar_url: string | null;
    color_theme: string | null;
}