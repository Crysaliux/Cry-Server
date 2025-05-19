import React, { Dispatch, SetStateAction, useContext } from "react";
import { GlobalContext } from '../services/context_manager';
import { useParams, useNavigate } from "react-router-dom";
import '../static/client_interface.css';

const ActionBarView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
    }
    const navigate = useNavigate();

    return (
        <>
            <div id="action-bar-addgroup" onClick={() => context_data.SetGroupModalStatus(true)}></div>
            <div id="action-bar-dms" onClick={() => navigate('/')}></div>
        </>
    );
};

export default React.memo(ActionBarView);