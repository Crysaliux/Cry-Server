import React, { useEffect, useState, Dispatch, SetStateAction, useContext } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { GlobalContext } from '../services/global_manager';
import '../static/client_interface.css';

const GroupsView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
    }
    const navigate = useNavigate();

    const HandleGroupNavigation = (id: string | number) => {
        context_data.SetCurrentGroupId(`${id}`);
        navigate(`/${id}`);
    };

    return (
        <>
            {context_data.groups.map(group => (
                <div className="group" key={group.id} data-owner_id={group.owner_id} data-desc={group.desc} onClick={() => HandleGroupNavigation(group.id)}>
                    <img src={group.icon_path}></img>
                </div>
            ))}
        </>
    );
};

export default React.memo(GroupsView);