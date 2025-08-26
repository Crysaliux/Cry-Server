import React, { createContext, Dispatch, ReactNode, SetStateAction, useState, memo, useRef, RefObject } from "react";
import { Client, Group, Room } from "components/index";

interface CoreGlobalProperties {
    api_oauth_addr: RefObject<string>;
    gateway_addr: RefObject<string>;
    api_hatch_addr: RefObject<string>;
    session_token: RefObject<string | null>;
    max_reconnection_attempts: RefObject<number>;
    reconnection_delay: RefObject<number>;
    max_reconnection_delay: RefObject<number>;
    message_sent_delta: RefObject<number>;
    client:RefObject<Client | null>;
    current_group: RefObject<Group | null>;
    current_room: RefObject<Room | null>;
}

interface CoreProperties {
    children: ReactNode;
}

export const CoreGlobalContext = createContext<CoreGlobalProperties | undefined>(undefined);

export const Core: React.FC<CoreProperties> = memo(({ children }) => {
    //GLOBAL CORE PROPERTIES/REFERENCES
    const api_oauth_addr = useRef<string>('localhost:8080/oauth/');
    const gateway_addr = useRef<string>('localhost:8080/gateway/');
    const api_hatch_addr = useRef<string>('localhost:8080/api_hatch/');
    const session_token = useRef<string | null>(null);
    const max_reconnection_attempts = useRef<number>(5);
    const reconnection_delay = useRef<number>(1000);
    const max_reconnection_delay = useRef<number>(5000);
    const message_sent_delta = useRef<number>(60000); //milliseconds
    const client = useRef<Client | null>(null);
    const current_group = useRef<Group | null>(null);
    const current_room = useRef<Room | null>(null);

    return (
        <CoreGlobalContext.Provider value = {{
            api_oauth_addr,
            gateway_addr,
            api_hatch_addr,
            session_token,
            max_reconnection_attempts,
            reconnection_delay,
            max_reconnection_delay,
            message_sent_delta,
            client,
            current_group,
            current_room,
        }}>
            { children }
        </CoreGlobalContext.Provider>
    );
});