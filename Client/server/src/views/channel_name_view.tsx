import React, { useContext } from "react";
import { useParams } from "react-router-dom";
import { GlobalContext } from '../services/global_manager';

const ChannelNameView: React.FC = () => {
    const { group_id, channel_id } = useParams<{ group_id: string, channel_id: string}>();
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for channel_name_view can't be defined.");
    }
    const RelatedChannel = context_data.channels.find(channel => channel.id === channel_id);

    return (
        <>
            {
                RelatedChannel ?
                <div id="channel-name-field">{RelatedChannel.name}</div>
                : null
            }
        </>
    );
};

export default React.memo(ChannelNameView);