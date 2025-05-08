import React, { Dispatch } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Channel } from "../components/channels";
import '../static/client_interface.css';

interface ChannelsViewProperties {
    channels: Channel[];
    set_current_channel_id: Dispatch<React.SetStateAction<string | null>>;
}

const ChannelsView: React.FC<ChannelsViewProperties> = ({ channels, set_current_channel_id }) => {
    const group_id = useParams<{ group_id: string}>();
    const navigate = useNavigate();
    const RelatedChannels = channels.filter(channel => channel.group_id === group_id);
    
    const HandleChannelNavigation = (id: string | number) => {
        set_current_channel_id(`${id}`);
        navigate(`/${group_id}/${id}`);
    };

    return (
        <>
            {RelatedChannels.map(channel => (
                <div className="channel medium nocopy" key={channel.id} data-group_id={group_id} data-name={channel.name} onClick={() => HandleChannelNavigation(channel.id)}># {channel.name}</div>
            ))}
        </>
    );
};

export default React.memo(ChannelsView);