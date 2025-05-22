import React, { useState, createContext, Dispatch, SetStateAction, useMemo } from 'react';
import { Routes, Route, BrowserRouter, useNavigate } from 'react-router-dom';
import { ContextManager } from './services/global_manager';
import { Listener } from './services/listener';
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
            <Listener>
                <BrowserRouter>
                    <div id="container">
                        <ErrorView />
                        <ModalView />

                        <div id="widgets">

                            <div id="header-widget" className="widget"></div>
                    
                            <div id="groups-widget" className="widget">
                                <GroupsView />
                                <div id="groups-widget-action-bar">
                                    <ActionBarView />
                                </div>
                            </div>

                            <div id="channels-contacts-widget" className="widget">
                                <Routes>
                                    <Route path="/" />
                                    <Route path="/:group_id" element={<ChannelsView />} />
                                </Routes>
                            </div>

                            <div id="chat-widget" className="widget">
                                <Routes>
                                    <Route path="/:contact_id" />
                                    <Route path="/:group_id/:channel_id" element={<ChannelView />} />
                                </Routes>
                            </div>

                            <div id="members-contact-widget" className="widget">
                                <Routes>
                                    <Route path="/:group_id" element={<MembersInfoView />} />
                                </Routes>
                            </div>

                            <div id="member-info-popup-widget" className="popup-widget"></div>
                            <div id="client-info-popup-widget" className="popup-widget"></div>
                            <div id="channel-settings-popup-widget" className="popup-widget"></div>
                            <div id="group-settings-popup-widget" className="popup-widget"></div>
                        </div>
                    </div>
                </BrowserRouter>
            </Listener>
        </ContextManager>
    );
};

export default App;