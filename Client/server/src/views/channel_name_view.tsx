import React, { useContext } from "react";
import { GlobalContext } from '../services/global_manager';

const ChannelNameView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for channel_name_view can't be defined.");
    }

    return (null);
};

export default React.memo(ChannelNameView);