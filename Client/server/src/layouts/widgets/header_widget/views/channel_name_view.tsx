import React, { useContext, useRef } from "react";
import { useParams } from "react-router-dom";
import { Channel } from "components/interface/channels";
import { GlobalContext } from 'services/global_manager';

const ChannelNameView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for channel_name_view can't be defined.");
    }
    const RelatedChannel = useRef<Channel>(undefined);
    
    if (context_data.current_channel_id.current) {
        RelatedChannel.current = context_data.channels.find(channel => channel.id === context_data.current_channel_id.current);
    }

    return (
        <>
            {
                RelatedChannel.current ?
                <div id="channel-name-field">{RelatedChannel.current.name}</div>
                : null
            }
        </>
    );
};

export default React.memo(ChannelNameView);