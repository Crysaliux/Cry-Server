export interface Contact {
    type: 'contact';
    id: number;
    co_client_id: number;
    co_client_name: string;
}

//ServerRequests

export interface ToRemoveContact {
    type: 'contact_remove';
    id: number;
}

export interface ContactCreationStatus {
    type: 'contact_creation_status';
    status: boolean;
    error: string | null;
}

/*
Updates are handled automatically when client receives partial representation of an initial interface (Contact)
*/