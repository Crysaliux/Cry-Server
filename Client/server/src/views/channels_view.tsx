import React, { Dispatch, SetStateAction, useContext } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { GlobalContext } from '../services/global_manager';
import '../static/client_interface.css';

const ChannelsView: React.FC = () => {
    const group_id = useParams<{ group_id: string}>();
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for channels_view can't be defined.");
    }
    const navigate = useNavigate();
    const RelatedChannels = context_data.channels.filter(channel => channel.group_id === group_id);
    
    const HandleChannelNavigation = (id: string | number) => {
        context_data.current_channel_id.current = `${id}`;
        navigate(`/${group_id}/${id}`);
    };

    return (
        <>
            {RelatedChannels.map(channel => (
                <div className="channel medium nocopy" key={channel.id} data-creator_id={channel.creator_id} data-group_id={group_id} data-name={channel.name} onClick={() => HandleChannelNavigation(channel.id)}># {channel.name}</div>
            ))}
        </>
    );
};

export default React.memo(ChannelsView);