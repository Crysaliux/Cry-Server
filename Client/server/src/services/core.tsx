import React, { createContext, Dispatch, ReactNode, SetStateAction, useState, memo, useRef, RefObject } from "react";

interface CoreContextGlobalProperties {
    
}

interface CoreContextManagerProperties {
    children: ReactNode;
}

export const CoreGlobalContext = createContext<CoreContextGlobalProperties | undefined>(undefined);

export const CoreContextManager: React.FC<CoreContextManagerProperties> = memo(({ children }) => {
    //GLOBAL CORE PROPERTIES/REFERENCES
    const api_oauth_addr = useRef<string>('localhost:8080/oauth/');
    const client = useRef<Client | null>(null);
    const current_group = useRef<Group | null>(null);
    const current_room = useRef<Room | null>(null);

    //GLOBAL SETTINGS

    const modal_input_field_short_length = useRef<number>(32);
    const modal_input_field_long_length = useRef<number>(256);

    return (
        <GlobalContext.Provider value = {{
            listener_addr,
            client_id,
            current_group_id,
            SetCurrentGroupId,
            current_channel_id,
            SetCurrentChannelId,
            current_modal,
            current_modal_failed_attempt,

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
            SetError,
            group_action_menu_display_status,
            SetGroupActionMenuDisplayStatus,

            modal_input_field_short_length,
            modal_input_field_long_length,
        }}>
            { children }
        </GlobalContext.Provider>
    );
});