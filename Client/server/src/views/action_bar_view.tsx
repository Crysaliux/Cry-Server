import React, { Dispatch, SetStateAction, useContext } from "react";
import { GlobalContext } from '../services/global_manager';
import { useParams, useNavigate } from "react-router-dom";
import { Modal } from "../components/overlay/modal";
import { Field } from "../components/overlay/field";
import '../static/client_interface.css';

const ActionBarView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for action_bar_View can't be defined.");
    }
    const navigate = useNavigate();

    const CreateGroupModal = () => {
        const NewModal: Modal = {
            type: 'modal',
            id: null,
            index: 'group',
            image_select: true,
            image_select_path: null,
            submit_colour: '',
            fields: [ 
                { "type": "field", "index": "name", "header": "What should we call it?", "input_length": "short", "input": '', "display": true },
                { "type": "field", "index": "desc", "header": "How would you describe it?", "input_length": "long", "input": '', "display": true },
            ] as Field[]
        };
        context_data.current_modal.current = NewModal;
        context_data.SetModalDisplayStatus(true);
    };

    return (
        <>
            <div id="action-bar-addgroup" onClick={CreateGroupModal}></div>
            <div id="action-bar-dms" onClick={() => navigate('/')}></div>
        </>
    );
};

export default React.memo(ActionBarView);