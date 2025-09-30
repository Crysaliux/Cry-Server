import React, { useState, createContext, Dispatch, SetStateAction, useMemo } from "react";
import { Routes, Route, BrowserRouter, useNavigate, Outlet } from "react-router-dom";
import { CookiesProvider } from "react-cookie";
import GroupLayout from "layouts/group_layout";
import LoginLayout from "layouts/login_layout";
import MainPageLayout from "layouts/main_page_layout";
import SignUpLayout from "layouts/signup_layout";
import RoomLayout from "layouts/room_layout";
import LoadingLayout from "layouts/loading_layout";
import { Listener } from "services/listener";
import { APIListener } from "services/api_listener";
import { Authentication } from "services/oauth";
import { Core } from "services/core";
import { ErrorAssessor } from "services/error_assessor";

//:group_id can represent group's global_name as well

const App: React.FC = () => {
    return (
        <BrowserRouter> 
                <Core>
                    <ErrorAssessor>
                    <APIListener>
                    <Authentication>
                    <Listener>
                        <Routes>
                            <Route path="/" element={<Outlet />}>
                                <Route index element={<MainPageLayout />} />
                                <Route path="oauth2/signup" element={<SignUpLayout />} />
                                <Route path="oauth2/login" element={<LoginLayout />} />

                                <Route path=":group_id" element={<GroupLayout />}>
                                    <Route path=":room_id" element={<RoomLayout />} />
                                </Route>
                            </Route>
                        </Routes>
                    </Listener>
                    </Authentication>
                    </APIListener>
                    </ErrorAssessor>
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