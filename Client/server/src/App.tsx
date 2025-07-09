import React, { useState, createContext, Dispatch, SetStateAction, useMemo } from 'react';
import { Routes, Route, BrowserRouter, useNavigate, Outlet } from 'react-router-dom';
import { ContextManager } from 'services/global_manager';
import { Listener } from 'services/listener';
import ChannelsLayout from 'layouts/widgets/channels_widget/channels_layout';
import ChatLayout from 'layouts/widgets/chat_widget/chat_layout';
//import ConntactsLayout from 'layouts/widgets/contacts_widget/contacts_layout';
import GroupsLayout from 'layouts/widgets/groups_widget/groups_layout';
import HeaderLayout from 'layouts/widgets/header_widget/header_layout';
import MembersLayout from 'layouts/widgets/members_widget/members_layout';
import OverlayLayout from 'layouts/widgets/overlay_widget/overlay_layout';
import GroupActionMenuLayout from 'layouts/popup_widgets/group_action_menu_widget/group_action_menu_layout';

interface GlobalLayoutInterface {
    to_load: string;
}

const GlobalLayout: React.FC<GlobalLayoutInterface> = ({ to_load }) => {
    switch(to_load) {
        case 'group':
            return (
                    <>
                        <OverlayLayout />
                        <div id="widgets">
                            <HeaderLayout to_load='group' />
                            <GroupsLayout />
                            <Outlet />
                            <ChannelsLayout />
                            <MembersLayout />
                            <GroupActionMenuLayout />
                        </div>
                    </>
            );
        case 'contacts':
            return (
                    <>
                        <OverlayLayout />
                        <div id="widgets">
                            <HeaderLayout to_load='contacts' />
                            <GroupsLayout />
                            <Outlet />
                        </div>
                    </>
            );
    }
};

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
                        <Routes>
                            <Route path="/" element={<GlobalLayout to_load='contacts' />}>

                            </Route>
                            <Route path="/group/:group_id" element={<GlobalLayout to_load='group' />}>
                                <Route path=":channel_id" element={<ChatLayout />} />
                            </Route>
                        </Routes>
                    </div>
                </Listener>
            </BrowserRouter>
        </ContextManager>
    );
};

export default App;