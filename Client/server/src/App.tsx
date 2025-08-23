import React, { useState, createContext, Dispatch, SetStateAction, useMemo } from 'react';
import { Routes, Route, BrowserRouter, useNavigate, Outlet } from 'react-router-dom';
import GroupLayout from 'layouts/group_layout';
import LoginLayout from 'layouts/login_layout';
import MainPageLayout from 'layouts/main_page_layout';
import SignUpLayout from 'layouts/signup_layout';
import RoomLayout from 'layouts/room_layout';
import { Listener } from 'services/listener';
import { Core } from 'services/core';

const App: React.FC = () => { //Logically correct, yet usable?
    return (
        <BrowserRouter>
            <Core>
                <Listener>
                    <div id="container">
                        <Routes>
                            <Route path="/" element={<Outlet />}>
                                <Route index element={<MainPageLayout />} />
                                <Route path="oauth2/signup" element={<SignUpLayout />} />
                                <Route path="oauth2/login" element={<LoginLayout />} />

                                <Route path=":group_global_name" element={<GroupLayout />}>
                                    <Route path=":room_id" element={<RoomLayout />}>
                                        <Route path=":mesage_id" element={} />
                                    </Route>
                                </Route>
                            </Route>
                        </Routes>
                    </div>
                </Listener>
            </Core>
        </BrowserRouter>
    );

    /*return (
        <BrowserRouter>
        <Context.Provider value={contextValue}>
            <HeaderLayout />
            <OverlayLayout />
            <GroupActionMenuLayout />
            <Routes>
            <Route path="/" element={<Outlet />}>
                <Route index element={<ChannelsLayout />} />
                <Route path="chat" element={<ChatLayout />} />
                <Route path="groups" element={<GroupsLayout />} />
                <Route path="members" element={<MembersLayout />} />
            </Route>
            </Routes>
        </Context.Provider>
        </BrowserRouter>
    ); */
};

export default App;