import React, { useEffect, useState, Dispatch, SetStateAction, useContext } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { GlobalContext } from 'services/client_core';
import { ListenerHatch } from 'services/listener';

const GroupsView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    const listener_hatch = useContext(ListenerHatch);
    if (!context_data || !listener_hatch) {
        throw new Error("Context for groups_view can't be defined.");
    }
    const navigate = useNavigate();

    const HandleGroupNavigation = (id: number) => {
        const RelatedChannels = context_data.channels.filter(channel => channel.group_id === id);
        listener_hatch.SendRequest({ type: 'group_request_members', id: id });
        context_data.SetCurrentGroupId(id);
        context_data.SetCurrentChannelId(RelatedChannels[0].id);
        navigate(`/group/${id}/${RelatedChannels[0].id}`);
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