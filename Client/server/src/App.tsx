import React, { useState, createContext, Dispatch, SetStateAction, useMemo } from "react";
import { Routes, Route, BrowserRouter, useNavigate, Outlet } from "react-router-dom";
import GroupLayout from "layouts/group_layout";
import LoginLayoutLoader from "layouts/login_layout";
import MainPageLayout from "layouts/main_page_layout";
import SignUpLayoutLoader from "layouts/signup_layout";
import RoomLayout, { RoomVoid } from "layouts/room_layout";
import { CreateGroupModal, CreateRoomModal } from "layouts/modal_layouts";
import { Listener } from "services/listener";
import { APIListener } from "services/api_listener";
import { Authentication } from "services/oauth";
import { Core } from "services/core";
import { ErrorAssessor } from "services/error_assessor";
import { PathSanitizer } from "services/path_sanitizer";

//:group_id can represent group's global_name as well

const App: React.FC = () => {
    return (
        <BrowserRouter> 
                <Core>
                    <PathSanitizer />
                    <ErrorAssessor>
                    <APIListener>
                    <Authentication>
                    <Listener>
                        <Routes>
                            <Route path="/" element={<Outlet />}>
                                <Route index element={<MainPageLayout />} />
                                <Route path="oauth2/signup" element={<SignUpLayoutLoader />} />
                                <Route path="oauth2/login" element={<LoginLayoutLoader />} />

                                <Route path=":group_global_name" element={<GroupLayout />}>
                                    <Route path=":room_id" element={<RoomLayout />}>
                                        <Route path="create_group" element={<CreateGroupModal/>} />
                                        <Route path="create_room" element={<CreateRoomModal/>} />
                                    </Route>
                                    <Route path="void" element={<RoomVoid />}>
                                        <Route path="create_group" element={<CreateGroupModal/>} />
                                        <Route path="create_room" element={<CreateRoomModal/>} />
                                    </Route>
                                </Route>

                                <Route path="dms" element={<GroupLayout />}>
                                    <Route path="create_group" element={<CreateGroupModal/>} />
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