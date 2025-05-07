import React, { useState } from 'react';
import { Routes, Route, BrowserRouter, useNavigate } from 'react-router-dom';
import { Contact } from "components/contacts";
import { Group } from "components/groups";
import { Channel } from "components/channels";
import { Message } from "components/messages";
import { Member } from "components/members";
import { Listener } from 'services/listener';
import GroupsView from 'views/groups_view';
import ChannelsView from 'views/channels_view';
import ChannelView from 'views/channel_view';
import ActionBarView from 'views/action_bar_view';
import '../static/client_interface.css';

const App: React.FC = () => {
    const [current_group_id, SetCurrentGroupId] = useState<string | null>(null);
    const [current_group_members, SetCurrentGroupMembers] = useState<Member[]>([]);

    const [current_channel_id, SetCurrentChannelId] = useState<string | null>(null);
    
    const [contacts, SetContacts] = useState<Contact[]>([]);
    const [groups, SetGroups] = useState<Group[]>([]);
    const [channels, SetChannels] = useState<Channel[]>([]);
    const [messages, SetMessages] = useState<Message[]>([]);

    const SendRequest = Listener("ws://somehost/listener", SetContacts, SetGroups, SetChannels, SetMessages);
    const navigate = useNavigate();
    
    /*
    Objects are edited upon receiving an update request from the API.
    MESSAGE_EDIT,
    CHANNEL_EDIT,
    GROUP_EDIT,
    */

    const MessageEdit = (data: Message, new_data: Partial<Message>) => {
        SetMessages((previous) => previous.map((message) => message.id === data.id ? { ...message, ...new_data } : message));
    };

    const ChannelEdit = (data: Channel, new_data: Partial<Channel>) => {
        SetChannels((previous) => previous.map((channel) => channel.id === data.id ? { ...channel, ...new_data } : channel));
    };

    const GroupEdit = (data: Group, new_data: Partial<Group>) => {
        SetGroups((previous) => previous.map((group) => group.id === data.id ? { ...group, ...new_data } : group));
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
                        <GroupsView groups={groups}/>
                        <div id="groups-widget-action-bar">
                            <ActionBarView />
                        </div>
                    </div>

                    <div id="channels-contacts-widget" className="widget">
                        <Routes>
                            <Route path="/" element={<ContactsView />} />
                            <Route path="/:group_id" element={<ChannelsView channels={channels}/>} />
                        </Routes>
                    </div>

                    <div id="chat-widget" className="widget">
                        <Routes>
                            <Route path="/:contact_id" element={<ContactView />} />
                            <Route path="/:group_id/:channel_id" element={<ChannelView messages={messages}/>} />
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
    );
};

export default App;