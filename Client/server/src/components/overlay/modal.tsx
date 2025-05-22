import { Field } from "./field";
/*
Modal types:
- group_creation
- channel_creation
- custom

ModalResponse types:
- group_modal_status
- channel_modal_status
- custom_modal_status
*/

//ServerRequests

export interface Modal {
    type: string;
    image_select: boolean;
    fields: Field[];
}

export interface ModalStatus {
    type: string;
    status: boolean;
}