import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import '../static/client_interface.css';


const ActionBarView: React.FC = () => {
    const navigate = useNavigate();

    return (
        <>
            <div id="action-bar-addgroup" onClick={}></div>
            <div id="action-bar-dms" onClick={() => navigate('/')}></div>
        </>
    );
};

export default React.memo(ActionBarView);