import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Group } from "../components/groups";
import '../static/client_interface.css';

interface GroupsViewProperties {
    groups: Group[];
}

const GroupsView: React.FC<GroupsViewProperties> = ({ groups }) => {
    const navigate = useNavigate();

    const HandleGroupNavigation = (id: string | number) => {
        navigate(`/${id}`);
    };

    return (
        <>
            {groups.map(group => (
                <div className="group" key={group.id} data-owner_id={group.owner_id} data-desc={group.desc} onClick={() => HandleGroupNavigation(group.id)}>
                    <img src={group.icon_path}></img>
                </div>
            ))}
        </>
    );
};

export default React.memo(GroupsView);