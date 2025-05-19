import React, { createContext, Dispatch, ReactNode, SetStateAction, useState } from "react";
import { Contact } from "../components/contacts";
import { Group } from "../components/groups";
import { Channel } from "../components/channels";
import { Message } from "../components/messages";
import { Member } from "../components/members";


interface ContextGlobalProperties {
    client_id: number | null,
    SetClientId: Dispatch<SetStateAction<number | null>>;
    client_name: string | null,
    SetClientName: Dispatch<SetStateAction<string | null>>;
    current_group_id: string | null;
    SetCurrentGroupId: Dispatch<SetStateAction<string | null>>;
    current_channel_id: string | null;
    SetCurrentChannelId: Dispatch<SetStateAction<string | null>>;
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
    group_modal_status: boolean;
    SetGroupModalStatus: Dispatch<SetStateAction<boolean>>;
    channel_modal_status: boolean;
    SetChannelModalStatus: Dispatch<SetStateAction<boolean>>;
    group_to_create: Group | null;
    SetGroupToCreate: Dispatch<SetStateAction<Group | null>>;
    channel_to_create: Channel | null;
    SetChannelToCreate: Dispatch<SetStateAction<Channel | null>>;
    error: string | null;
    SetError: Dispatch<SetStateAction<string | null>>;
}

interface ContextManagerProperties {
    children: ReactNode;
}

export const GlobalContext = createContext<ContextGlobalProperties | undefined>(undefined);

export const ContextManager: React.FC<ContextManagerProperties> = ({ children }) => {
    //GLOBAL PROPERTIES
    const [client_id, SetClientId] = useState<number | null>(null);
    const [client_name, SetClientName] = useState<string | null>(null);
            
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

    return (
        <GlobalContext.Provider value = {{ 
            client_id,
            SetClientId,
            client_name,
            SetClientName,
            current_group_id, 
            SetCurrentGroupId,
            current_channel_id,
            SetCurrentChannelId,
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
            group_modal_status, 
            SetGroupModalStatus,
            channel_modal_status, 
            SetChannelModalStatus,
            group_to_create, 
            SetGroupToCreate,
            channel_to_create,
            SetChannelToCreate,
            error,
            SetError
        }}>
            {children}
        </GlobalContext.Provider>
    );
};