import React, { useState } from 'react';
import { Routes, Route, BrowserRouter, useNavigate } from 'react-router-dom';
import { Listener } from 'services/listener';
import { GroupView } from 'views/group_view';
import { Message } from "components/messages";
import './App.css'

const App: React.FC = () => {
    const [current_group_id, SetCurrentGroupId] = useState<string | null>(null);
    const [current_channel_id, SetCurrentChannelId] = useState<string | null>(null);
    const [unread_messages, AddUnreadMessages] = useState<Message[]>([]);
    const { groups, contacts, channels, messages } = Listener("ws://somehost/listener", current_group_id, current_channel_id);
    const navigate = useNavigate();

    const HandleGroupNavigation = (id: string | number) => {
        navigate(`/${id}`);
    };

    return (
        <BrowserRouter>
            <div id="container">
                <div id="overlays">
                    <div id="client-overlay"></div>
                    <div id="modal-overlay"></div>
                </div>
                <div id="widgets">
                    <div id="header-widget" className="widget"></div>
                    <div id="groups-widget" className="widget">
                        {groups.map((group) => (
                            <div className="group" key={group.id} data-owner_id={group.owner_id} data-desc={group.desc} onClick={() => HandleGroupNavigation(group.id)}>
                                <img src={group.icon_path}></img>
                            </div>
                        ))}
                        <div id="groups-widget-action-bar">
                            <div id="action-bar-addgroup"></div>
                            <div id="action-bar-dms"></div>
                        </div>
                    </div>
                    <div id="channels-contacts-widget" className="widget"></div>
                    <div id="chat-widget" className="widget"></div>
                    <div id="members-contact-widget" className="widget"></div>
                    <div id="member-info-popup-widget" className="popup-widget"></div>
                    <div id="client-info-popup-widget" className="popup-widget"></div>
                    <div id="channel-settings-popup-widget" className="popup-widget"></div>
                    <div id="group-settings-popup-widget" className="popup-widget"></div>
                </div>
                <Routes>
                    <Route path="/:group_id" element={<GroupView />}>
                        <Route path="/:channel_id" element={<Channel />} />
                    </Route>
                    <Route path="/" element={<Contacts />}>
                        <Route path="/:contact_id" element={<Contact />} />
                    </Route>
                </Routes>
            </div>
        </BrowserRouter>
    );
};

export default App;