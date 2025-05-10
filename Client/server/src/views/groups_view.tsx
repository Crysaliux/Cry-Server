import React, { useEffect, useState, Dispatch, SetStateAction } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Group } from "../components/groups";
import '../static/client_interface.css';

interface GroupsViewProperties {
    groups: Group[];
    set_current_group_id: Dispatch<SetStateAction<string | null>>;
}

const GroupsView: React.FC<GroupsViewProperties> = ({ groups, set_current_group_id }) => {
    const navigate = useNavigate();

    const HandleGroupNavigation = (id: string | number) => {
        set_current_group_id(`${id}`);
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