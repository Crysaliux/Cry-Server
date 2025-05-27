import React from "react";
import GroupInfoView from '../group_info_view';
import MembersStatsView from '../members_stats_view';
import ChannelsView from '../channels_view';
import MembersInfoView from '../members_info_view';
import { Outlet } from "react-router-dom";

const GroupLayout: React.FC = () => { //<ChannelNameView />, <ChannelView />

    return (
        <>
            <div id="header-widget" className="silent_widget">
                <div id="header-support-widget" className="widget">

                </div>
                <div id="header-group-addfriend-widget" className="widget">
                    <GroupInfoView />
                </div>
                <div id="header-channelinfo-contacts-widget" className="widget">
                    <Outlet />
                </div>
                <div id="header-memberstats-widget" className="widget">
                    <MembersStatsView />
                </div>
            </div>

            <div id="channels-contacts-widget" className="widget">
                <ChannelsView />
            </div>

            <div id="chat-widget" className="widget">
                <Outlet />
            </div>

            <div id="members-contact-widget" className="widget">
                <MembersInfoView />
            </div>
        </>
    );
};

export default React.memo(GroupLayout);