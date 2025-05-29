import React, { createContext, Dispatch, ReactNode, SetStateAction, useState, memo, useRef, RefObject } from "react";
import { Contact } from "components/interface/contacts";
import { Group } from "components/interface/groups";
import { Channel } from "components/interface/channels";
import { Message } from "components/interface/messages";
import { Member } from "components/interface/members";
import { Modal } from "components/overlay/modal";
import { FriendRequest } from "components/interface/friend_requests";


interface ContextGlobalProperties {
    listener_addr: RefObject<string>;
    client_id: RefObject<number | null>;
    current_group_id: string | null;
    SetCurrentGroupId: Dispatch<SetStateAction<string | null>>;
    current_channel_id: string | null;
    SetCurrentChannelId: Dispatch<SetStateAction<string | null>>;
    current_modal: RefObject<Modal | null>;

    client_display_name: string | null;
    SetClientDisplayName: Dispatch<SetStateAction<string | null>>;
    client_username: string | null;
    SetClientUsername: Dispatch<SetStateAction<string | null>>;

    current_group_members: Member[];
    SetCurrentGroupMembers: Dispatch<SetStateAction<Member[]>>;
    contacts: Contact[];
    SetContacts: Dispatch<SetStateAction<Contact[]>>;
    groups: Group[];
    SetGroups: Dispatch<SetStateAction<Group[]>>;
    channels: Channel[];
    SetChannels: Dispatch<SetStateAction<Channel[]>>;
    messages: Message[];
    SetMessages: Dispatch<SetStateAction<Message[]>>;
    friend_requests: FriendRequest[];
    SetFriendRequests: Dispatch<SetStateAction<FriendRequest[]>>;

    modal_display_status: boolean;
    SetModalDisplayStatus: Dispatch<SetStateAction<boolean>>;
    modal_submit_request: Modal | null; 
    SetModalSubmitRequest: Dispatch<SetStateAction<Modal | null>>;
    error: string | null;

    SetError: Dispatch<SetStateAction<string | null>>;
}

interface ContextManagerProperties {
    children: ReactNode;
}

export const GlobalContext = createContext<ContextGlobalProperties | undefined>(undefined);

export const ContextManager: React.FC<ContextManagerProperties> = memo(({ children }) => {
    //GLOBAL PROPERTIES/REFERENCES
    const listener_addr = useRef<string>('ws://localhost:8080/client/api');
    const client_id = useRef<number | null>(1234);
    const [current_group_id, SetCurrentGroupId] = useState<string | null>(null);
    const [current_channel_id, SetCurrentChannelId] = useState<string | null>(null);
    const current_modal = useRef<Modal | null>(null);

    const [client_display_name, SetClientDisplayName] = useState<string | null>(null);
    const [client_username, SetClientUsername] = useState<string | null>(null);

    const [current_group_members, SetCurrentGroupMembers] = useState<Member[]>([]);
    const [contacts, SetContacts] = useState<Contact[]>([]);
    const [groups, SetGroups] = useState<Group[]>([]);
    const [channels, SetChannels] = useState<Channel[]>([]);
    const [messages, SetMessages] = useState<Message[]>([]);
    const [friend_requests, SetFriendRequests] = useState<FriendRequest[]>([]);
            
    const [modal_display_status, SetModalDisplayStatus] = useState<boolean>(false);
    const [modal_submit_request, SetModalSubmitRequest] = useState<Modal | null>(null);
            
    const [error, SetError] = useState<string | null>(null);

    return (
        <GlobalContext.Provider value = {{
            listener_addr,
            client_id,
            current_group_id,
            SetCurrentGroupId,
            current_channel_id,
            SetCurrentChannelId,
            current_modal,

            client_display_name,
            SetClientDisplayName,
            client_username,
            SetClientUsername,
            current_group_members, 
            SetCurrentGroupMembers,
            contacts, 
            SetContacts,
            groups, 
            SetGroups,
            channels, 
            SetChannels,
            messages, 
            SetMessages,
            friend_requests,
            SetFriendRequests,

            modal_display_status,
            SetModalDisplayStatus,
            modal_submit_request,
            SetModalSubmitRequest,
            error,
            SetError
        }}>
            { children }
        </GlobalContext.Provider>
    );
});