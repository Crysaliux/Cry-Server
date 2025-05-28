import React from "react";
import ChannelView from './views/channel_view';

const ChatLayout: React.FC = () => {
    return (
        <div id="chat-widget" className="widget">
            <ChannelView />
        </div>
    );
};

export default React.memo(ChatLayout);