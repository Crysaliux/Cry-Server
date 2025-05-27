import React, { useState, createContext, Dispatch, SetStateAction, useMemo } from 'react';
import { Routes, Route, BrowserRouter, useNavigate, Outlet } from 'react-router-dom';
import { ContextManager } from './services/global_manager';
import { Listener } from './services/listener';
import GroupLayout from './views/layouts/group_layout';
import ContactsLayout from './views/layouts/contacts_layout';
import ChannelNameView from './views/channel_name_view';
import ChannelView from './views/channel_view';
import ModalView from './views/modal_view';
import GroupsView from './views/groups_view';
import ActionBarView from './views/action_bar_view';
import ErrorView from './views/error_view';
import './static/client_interface.css';
import './static/global_styles.css';


const App: React.FC = () => {
    //element={<ContactView />}
    //element={<ContactsView />}

    function Empty() {
        return null;
    }

    return (
        <ContextManager>
            <BrowserRouter>
                <Listener>
                    <div id="container">
                        <ErrorView />
                        <ModalView />

                        <div id="widgets">

                            <div id="groups-widget" className="widget">
                                <GroupsView />
                                <div id="groups-widget-action-bar">
                                    <ActionBarView />
                                </div>
                            </div>

                            <Routes>
                                <Route path="/group/:group_id" element={<GroupLayout />}>
                                    <Route path="/group/:group_id/:channel_id" element={<ChannelNameView />} />
                                    <Route path="/group/:group_id/:channel_id" element={<ChannelView />} />
                                </Route>
                                <Route path="/" element={<ContactsLayout />}>
                                    <Route path="/:contact_id" />
                                </Route>
                            </Routes>

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