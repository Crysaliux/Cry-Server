export interface Client {
    type: "client";
    username: string;
    nickname: string;
    about_me: string | null;
    avatar_url: string | null;
    color_theme: string | null;
}