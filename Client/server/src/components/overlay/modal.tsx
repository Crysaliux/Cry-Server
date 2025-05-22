import { Field } from "./field";
/*
Modal indexes:
- group_creation
- channel_creation
- custom

ModalResponse indexes:
- group_modal_status
- channel_modal_status
- custom_modal_status
*/

//ServerRequests

export interface Modal {
    type: 'modal';
    index: string;
    image_select: boolean;
    image_select_path: string | null;
    submit_colour: string;
    fields: Field[];
}

export interface ModalStatus {
    type: 'modal_status';
    index: string;
    status: boolean;
}