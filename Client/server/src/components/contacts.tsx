export interface Contact {
    type: 'contact';
    id: number | string;
    co_client_id: number | string;
    co_client_name: string;
}

export interface ToRemoveContact {
    type: 'contact_remove';
    id: number | string;
}