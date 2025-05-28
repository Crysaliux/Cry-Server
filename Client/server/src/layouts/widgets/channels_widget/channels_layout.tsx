import React from "react";
import ChannelsView from './views/channels_view';

const ChannelsLayout: React.FC = () => {
    return (
        <div id="channels-contacts-widget" className="widget">
            <ChannelsView />
        </div>
    );
};

export default React.memo(ChannelsLayout);