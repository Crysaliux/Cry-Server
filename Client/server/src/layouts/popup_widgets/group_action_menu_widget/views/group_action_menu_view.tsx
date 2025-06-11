import React, { useContext } from "react";
import { GlobalContext } from 'services/global_manager';
import { Modal } from "components/overlay/modal";
import { Field } from "components/overlay/field";

const GroupActionMenuView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for group_action_menu_view can't be defined.");
    }

    const CreateChannelModal = () => {
        const NewModal: Modal = {
            type: 'modal',
            id: null,
            index: 'channel',
            image_select: false,
            image_select_path: null,
            submit_colour: 'blue',
            submit_text: 'Create channel',
            fields: [ 
                { "type": "field", "index": "name", "header": "What should we call it?", "input_length": "short", "input": '', "display": true },
                { "type": "field", "index": "group_id", "header": "", "input_length": "", "input": context_data.current_group_id, "display": false },
            ] as Field[]
        };
        context_data.current_modal.current = NewModal;
        context_data.SetModalDisplayStatus(true);
    };

    return (
        <>
            <div className="group_action_menu_option transparent medium">
                <div className="group_action_menu_option_name" onClick={CreateChannelModal}>
                    New category
                </div>
                <div className="group_action_menu_option_icon">
                    <img></img>
                </div>
            </div>

            <div className="group_action_menu_option transparent medium">
                <div className="group_action_menu_option_name" onClick={CreateChannelModal}>
                    New channel
                </div>
                <div className="group_action_menu_option_icon">
                    <img></img>
                </div>
            </div>

            <div className="group_action_menu_option transparent medium">
                <div className="group_action_menu_option_name">
                    Settings
                </div>
                <div className="group_action_menu_option_icon">
                    <img></img>
                </div>
            </div>
        </>
    );
};

export default React.memo(GroupActionMenuView);