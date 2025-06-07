import React, { useContext, useRef } from "react";
import { GlobalContext } from 'services/global_manager';
import { Modal } from "components/overlay/modal";
import { Field } from "components/overlay/field";

const AddFriendView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for add_friend_view can't be defined.");
    }

    const button_native_colour = useRef<string>('green');
    const button_current_colour = useRef<string | null>(null)

    if (button_native_colour.current) {
        button_current_colour.current = button_native_colour.current
    }

    const SetColour = (colour: string) => {
        if (button_native_colour.current) {
            button_current_colour.current = colour
        } 
    };

    const CreateContactModal = () => {
        SetColour(`${button_native_colour.current}_clicked`);
        const NewModal: Modal = {
            type: 'modal',
            id: null,
            index: 'friend_request',
            image_select: false,
            image_select_path: null,
            submit_colour: 'blue',
            submit_text: 'Add friend',
            fields: [ 
                { "type": "field", "index": "username", "header": "Input their username", "input_length": "short", "input": '', "display": true },
            ] as Field[]
        };
        context_data.current_modal.current = NewModal;
        context_data.SetModalDisplayStatus(true);
        SetColour(button_native_colour.current);
    };

    return (
        <>
            <button className={`button ${button_current_colour.current} small nocopy`} onClick={CreateContactModal}>Add friend</button>
        </>
    );
};

export default React.memo(AddFriendView);