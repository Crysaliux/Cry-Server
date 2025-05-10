import React, { useState } from "react";
import '../static/client_interface.css';

interface ChannelModalViewProperties {
    channel_modal_status: boolean;
}

const ChannelModalView: React.FC<ChannelModalViewProperties> = ({ channel_modal_status }) => {

    if (channel_modal_status) {
        return (
            <>
            </>
        );
    } else {
        return null;
    }
};

export default ChannelModalView;