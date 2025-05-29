import React from "react";
import AddFriendView from './views/add_friend_view';
import ChannelNameView from './views/channel_name_view';
import ContactsActionBarView from './views/contacts_action_bar_view';
import GroupInfoView from './views/group_info_view';
import MemberStatsView from './views/members_stats_view';

interface HeaderLayoutInterface {
    to_load: string;
}

const HeaderLayout: React.FC<HeaderLayoutInterface> = ({ to_load }) => {
    switch(to_load) {
        case 'group':
            return (
                <div id="header-widget" className="silent_widget">
                    <div id="header-support-widget" className="widget">
        
                    </div>
                    <div id="header-group-addfriend-widget" className="widget">
                        <GroupInfoView />
                    </div>
                    <div id="header-channelinfo-contacts-widget" className="widget">
                        <ChannelNameView />
                    </div>
                    <div id="header-memberstats-widget" className="widget">
                        <MemberStatsView />
                    </div>
                </div>
            );
        case 'contacts':
            return (
                <div id="header-widget" className="silent_widget">
                    <div id="header-support-widget" className="widget">
        
                    </div>
                    <div id="header-group-addfriend-widget" className="widget">
                        <AddFriendView />
                    </div>
                    <div id="header-channelinfo-contacts-widget" className="widget">
                        <ContactsActionBarView />
                    </div>
                </div>
            );
        default:
            return null;
    }
};

export default HeaderLayout;