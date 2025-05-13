import React, { useState } from 'react';
import { Routes, Route, BrowserRouter, useNavigate } from 'react-router-dom';
import { Contact } from "./components/contacts";
import { Group } from "./components/groups";
import { Channel } from "./components/channels";
import { Message } from "./components/messages";
import { Member } from "./components/members";
import { Listener } from './services/listener';
import GroupsView from './views/groups_view';
import ChannelsView from './views/channels_view';
import ChannelView from './views/channel_view';
import ActionBarView from './views/action_bar_view';
import MembersInfoView from './views/members_info_view';
import GroupModalView from './views/group_modal_view';
import ChannelModalView from './views/channel_modal_view';
import ErrorView from './views/error_view';

const App: React.FC = () => {
    const client_id = 555;
    const [client_name, SetClientName] = useState<string>("test");

    const [current_group_id, SetCurrentGroupId] = useState<string | null>(null);
    const [current_channel_id, SetCurrentChannelId] = useState<string | null>(null);

    const [current_group_members, SetCurrentGroupMembers] = useState<Member[]>([]);
    const [contacts, SetContacts] = useState<Contact[]>([]);
    const [groups, SetGroups] = useState<Group[]>([]);
    const [channels, SetChannels] = useState<Channel[]>([]);
    const [messages, SetMessages] = useState<Message[]>([]);

    const [group_modal_status, SetGroupModalStatus] = useState<boolean>(false);
    const [channel_modal_status, SetChannelModalStatus] = useState<boolean>(false);

    const [group_to_create, SetGroupToCreate] = useState<Group | null>(null);
    const [channel_to_create, SetChannelToCreate] = useState<Channel | null>(null);

    const [error, SetError] = useState<string | null>(null);

    const SendRequest = Listener(
        "ws://26.102.83.29:8080/client/api",
        contacts,
        groups, 
        channels, 
        messages, 
        current_group_id, 
        group_to_create, 
        channel_to_create, 
        client_id,
        SetContacts, 
        SetGroups, 
        SetChannels, 
        SetMessages, 
        SetCurrentGroupMembers, 
        SetGroupToCreate, 
        SetChannelToCreate, 
        SetGroupModalStatus, 
        SetChannelModalStatus, 
        SetError
    ); 
    //element={<ContactView />}
    //element={<ContactsView />}

    return (
        <BrowserRouter>
            <div id="container">
                <ErrorView error={error} set_error={SetError} />
                <GroupModalView group_modal_status={group_modal_status} set_group_modal_status={SetGroupModalStatus} set_group_to_create={SetGroupToCreate} set_error={SetError} />
                <ChannelModalView channel_modal_status={channel_modal_status} set_channel_modal_status={SetChannelModalStatus} set_channel_to_create={SetChannelToCreate} current_group_id={current_group_id} set_error={SetError} />

                <div id="widgets">

                    <div id="header-widget" className="widget"></div>
                    
                    <div id="groups-widget" className="widget">
                        <GroupsView groups={groups} set_current_group_id={SetCurrentGroupId} />
                        <div id="groups-widget-action-bar">
                            <ActionBarView set_group_modal_status={SetGroupModalStatus} />
                        </div>
                    </div>

                    <div id="channels-contacts-widget" className="widget">
                        <Routes>
                            <Route path="/" />
                            <Route path="/:group_id" element={<ChannelsView channels={channels} set_current_channel_id={SetCurrentChannelId} />} />
                        </Routes>
                    </div>

                    <div id="chat-widget" className="widget">
                        <Routes>
                            <Route path="/:contact_id" />
                            <Route path="/:group_id/:channel_id" element={<ChannelView messages={messages} />} />
                        </Routes>
                    </div>

                    <div id="members-contact-widget" className="widget">
                        <Routes>
                            <Route path="/:group_id" element={<MembersInfoView members={current_group_members} />} />
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