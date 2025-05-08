export interface Contact {
    type: 'contact';
    id: number | string;
    co_client_id: number | string;
    co_client_name: string;
}

//ServerRequests

export interface ToRemoveContact {
    type: 'contact_remove';
    id: number | string;
}

/*
Updates are handled automatically when client receives partial representation of an initial interface (Contact)
*/