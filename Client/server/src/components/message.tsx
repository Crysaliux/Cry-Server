export interface Message {
    type: "message";
    client_id: string;
    nickname: string;
    content: string;
    id: string;
}

//To be completely redesigned! Mayhaps.