import React, { useState, createContext, Dispatch, SetStateAction, useMemo } from 'react';
import { Routes, Route, BrowserRouter, useNavigate } from 'react-router-dom';
import { ContextManager } from './services/global_manager';
import { Listener } from './services/listener';
import ChannelNameView from './views/channel_name_view';
import GroupInfoView from './views/group_info_view';
import MembersStatsView from './views/members_stats_view';
import AddFriendView from './views/add_friend_view';
import FriendNameView from './views/friend_name_view';
import GroupsView from './views/groups_view';
import ChannelsView from './views/channels_view';
import ChannelView from './views/channel_view';
import ActionBarView from './views/action_bar_view';
import MembersInfoView from './views/members_info_view';
import ModalView from './views/modal_view';
import ErrorView from './views/error_view';

const App: React.FC = () => {
    //element={<ContactView />}
    //element={<ContactsView />}

    return (
        <ContextManager>
            <BrowserRouter>
                <Listener>
                    <div id="container">
                        <ErrorView />
                        <ModalView />

                        <div id="widgets">

                            <div id="header-widget" className="silent_widget">
                                <div id="header-support-widget" className="widget">

                                </div>
                                <div id="header-group-addfriend-widget" className="widget">
                                    <Routes>
                                        <Route path="/" element={<AddFriendView /> } />
                                        <Route path="/group/:group_id" element={<GroupInfoView />} />
                                    </Routes>
                                </div>
                                <div id="header-channelinfo-friends-widget" className="widget">
                                    <Routes>
                                        <Route path="/:contact_id" element={<FriendNameView />} />
                                        <Route path="/group/:group_id/:channel_id" element={<ChannelNameView />} />
                                    </Routes>
                                </div>
                                <div id="header-memberstats-widget" className="widget">
                                    <Routes>
                                        <Route path="/group/:group_id" element={<MembersStatsView />} />
                                    </Routes>
                                </div>
                            </div>
                    
                            <div id="groups-widget" className="widget">
                                <GroupsView />
                                <div id="groups-widget-action-bar">
                                    <ActionBarView />
                                </div>
                            </div>

                            <div id="channels-contacts-widget" className="widget">
                                <Routes>
                                    <Route path="/" />
                                    <Route path="/group/:group_id" element={<ChannelsView />} />
                                </Routes>
                            </div>

                            <div id="chat-widget" className="widget">
                                <Routes>
                                    <Route path="/:contact_id" />
                                    <Route path="/group/:group_id/:channel_id" element={<ChannelView />} />
                                </Routes>
                            </div>

                            <div id="members-contact-widget" className="widget">
                                <Routes>
                                    <Route path="/group/:group_id" element={<MembersInfoView />} />
                                </Routes>
                            </div>

                            <div id="member-info-popup-widget" className="popup-widget"></div>
                            <div id="client-info-popup-widget" className="popup-widget"></div>
                            <div id="channel-settings-popup-widget" className="popup-widget"></div>
                            <div id="group-settings-popup-widget" className="popup-widget"></div>
                        </div>
                    </div>
                </Listener>
            </BrowserRouter>
        </ContextManager>
    );
};

export default App;