import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Channel } from "../components/channels";
import '../static/client_interface.css';

interface ChannelsViewProperties {
    channels: Channel[];
}

const ChannelsView: React.FC<ChannelsViewProperties> = ({ channels }) => {
    const group_id = useParams<{ group_id: string}>();
    const navigate = useNavigate();
    const RelatedChannels = channels.filter(channel => channel.group_id === group_id);
    
    const HandleChannelNavigation = (id: string | number) => {
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