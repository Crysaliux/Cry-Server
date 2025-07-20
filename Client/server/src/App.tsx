import React, { useState, createContext, Dispatch, SetStateAction, useMemo } from 'react';
import { Routes, Route, BrowserRouter, useNavigate, Outlet } from 'react-router-dom';
import { ContextManager } from 'services/core';
import { Listener } from 'services/listener';
import ChannelsLayout from 'layouts/widgets/channels_widget/channels_layout';
import ChatLayout from 'layouts/widgets/chat_widget/chat_layout';
//import ConntactsLayout from 'layouts/widgets/contacts_widget/contacts_layout';
import GroupsLayout from 'layouts/widgets/groups_widget/groups_layout';
import HeaderLayout from 'layouts/widgets/header_widget/header_layout';
import MembersLayout from 'layouts/widgets/members_widget/members_layout';
import OverlayLayout from 'layouts/widgets/overlay_widget/overlay_layout';
import GroupActionMenuLayout from 'layouts/popup_widgets/group_action_menu_widget/group_action_menu_layout';

const App: React.FC = () => {
    const [contextManager, setContextManager] = useState<ContextManager | null>(null);
    const [listener, setListener] = useState<Listener | null>(null);
    
    const contextValue = useMemo(() => ({
        contextManager,
        setContextManager,
        listener,
        setListener
    }), [contextManager, listener]);
    
    return (
        <BrowserRouter>
        <Context.Provider value={contextValue}>
            <HeaderLayout />
            <OverlayLayout />
            <GroupActionMenuLayout />
            <Routes>
            <Route path="/" element={<Outlet />}>
                <Route index element={<ChannelsLayout />} />
                <Route path="chat" element={<ChatLayout />} />
                {/* <Route path="contacts" element={<ConntactsLayout />} /> */}
                <Route path="groups" element={<GroupsLayout />} />
                <Route path="members" element={<MembersLayout />} />
            </Route>
            </Routes>
        </Context.Provider>
        </BrowserRouter>
    );
};

export default App;