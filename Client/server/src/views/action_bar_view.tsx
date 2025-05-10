import React, { Dispatch, SetStateAction } from "react";
import { useParams, useNavigate } from "react-router-dom";
import '../static/client_interface.css';

interface ActionBarViewProperties {
    set_group_modal_status: Dispatch<SetStateAction<boolean>>;
}

const ActionBarView: React.FC<ActionBarViewProperties> = ({ set_group_modal_status }) => {
    const navigate = useNavigate();

    return (
        <>
            <div id="action-bar-addgroup" onClick={() => set_group_modal_status(true)}></div>
            <div id="action-bar-dms" onClick={() => navigate('/')}></div>
        </>
    );
};

export default React.memo(ActionBarView);