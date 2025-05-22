import React, { Dispatch, SetStateAction, useContext } from "react";
import { GlobalContext } from '../services/global_manager';
import { useParams, useNavigate } from "react-router-dom";
import { Modal } from "../components/overlay/modal";
import { Field } from "../components/overlay/field";
import '../static/client_interface.css';

const ActionBarView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
    }
    const navigate = useNavigate();

    const CreateGroupModal = () => {
        const NewModal: Modal = {
            type: 'modal',
            index: 'create_group',
            image_select: true,
            image_select_path: null,
            submit_colour: 'grey',
            fields: [ 
                { "type": "field", "index": "name", "header": "What should we call it?", "input_length": "short", "input": '' },
                { "type": "field", "index": "desc", "header": "How would you describe it?", "input_length": "long", "input": '' },
            ] as Field[]
        };
        return NewModal;
    };

    return (
        <>
            <div id="action-bar-addgroup" onClick={() => context_data.SetDisplayModal(CreateGroupModal())}></div>
            <div id="action-bar-dms" onClick={() => navigate('/')}></div>
        </>
    );
};

export default React.memo(ActionBarView);