import React, { useEffect, useState, Dispatch, SetStateAction, useContext } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { GlobalContext } from '../services/global_manager';
import { ListenerHatch } from "../services/listener";
import '../static/client_interface.css';

const GroupsView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    const listener_hatch = useContext(ListenerHatch);
    if (!context_data || !listener_hatch) {
        throw new Error("Context for groups_view can't be defined.");
    }
    const navigate = useNavigate();

    const HandleGroupNavigation = (id: string | number) => {
        context_data.current_group_id.current = `${id}`;
        listener_hatch.SendRequest({ type: 'group_request_members', id: context_data.current_group_id.current });
        navigate(`/group/${id}`);
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