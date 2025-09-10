import React, { createContext, Dispatch, ReactNode, SetStateAction, useState, memo, useRef, RefObject } from "react";
import { Client, Group, Room } from "components/index";

interface CoreGlobalProperties {
    core_server_host: RefObject<string>;
    api_oauth_addr: RefObject<string>;
    gateway_addr: RefObject<string>;
    api_hatch_addr: RefObject<string>;
    max_reconnection_attempts: RefObject<number>;
    reconnection_delay: RefObject<number>;
    max_reconnection_delay: RefObject<number>;
    message_sent_delta: RefObject<number>;
    client:RefObject<Client | null>;
    current_group: RefObject<Group | null>;
    current_room: RefObject<Room | null>;
    session_token: string | null;
    setSessionToken: Dispatch<SetStateAction<string | null>>;
}

interface CoreProperties {
    children: ReactNode;
}

export const CoreGlobalContext = createContext<CoreGlobalProperties | undefined>(undefined);

export const Core: React.FC<CoreProperties> = memo(({ children }) => {
    //GLOBAL CORE PROPERTIES/REFERENCES
    const core_server_host = useRef<string>('http://localhost:8080');
    const api_oauth_addr = useRef<string>('/oauth');
    const gateway_addr = useRef<string>('/gateway/socket.io');
    const api_hatch_addr = useRef<string>('/api');

    const max_reconnection_attempts = useRef<number>(5);
    const reconnection_delay = useRef<number>(1000);
    const max_reconnection_delay = useRef<number>(5000);
    const message_sent_delta = useRef<number>(60000); //milliseconds

    const client = useRef<Client | null>(null);
    const current_group = useRef<Group | null>(null);
    const current_room = useRef<Room | null>(null);

    const [session_token, setSessionToken] = useState<string | null>(null);

    return (
        <CoreGlobalContext.Provider value = {{
            core_server_host,
            api_oauth_addr,
            gateway_addr,
            api_hatch_addr,
            max_reconnection_attempts,
            reconnection_delay,
            max_reconnection_delay,
            message_sent_delta,
            client,
            current_group,
            current_room,
            session_token,
            setSessionToken,
        }}>
            { children }
        </CoreGlobalContext.Provider>
    );
});