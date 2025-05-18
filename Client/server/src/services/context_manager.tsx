import { createContext, Dispatch, SetStateAction } from "react";
import { Contact } from "../components/contacts";
import { Group } from "../components/groups";
import { Channel } from "../components/channels";
import { Message } from "../components/messages";
import { Member } from "../components/members";


interface GlobalProperties {
    current_group_id: string | null;
    set_current_group_id: Dispatch<SetStateAction<string | null>>;
    current_channel_id: string | null;
    set_current_channel_id: Dispatch<SetStateAction<string | null>>;
    current_group_members: Member[];
    set_current_group_members: Dispatch<SetStateAction<Member[]>>;
    contacts: Contact[];
    set_contacts: Dispatch<SetStateAction<Contact[]>>;
    groups: Group[];
    set_groups: Dispatch<SetStateAction<Group[]>>;
    channels: Channel[];
    set_channels: Dispatch<SetStateAction<Channel[]>>;
    messages: Message[];
    set_messages: Dispatch<SetStateAction<Message[]>>;
    group_modal_status: boolean;
    set_group_modal_status: Dispatch<SetStateAction<boolean>>;
    channel_modal_status: boolean;
    set_channel_modal_status: Dispatch<SetStateAction<boolean>>;
    group_to_create: Group | null;
    set_group_to_create: Dispatch<SetStateAction<Group | null>>;
    channel_to_create: Channel | null;
    set_channel_to_create: Dispatch<SetStateAction<Channel | null>>;
    error: string | null;
    set_error: Dispatch<SetStateAction<string | null>>;
}

export const GlobalContext = createContext<GlobalProperties | undefined>(undefined);