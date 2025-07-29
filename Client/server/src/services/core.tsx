import React, { createContext, Dispatch, ReactNode, SetStateAction, useState, memo, useRef, RefObject } from "react";
import { Client, Group, Room } from "components/index";

interface CoreGlobalProperties {
    api_oauth_addr: RefObject<string>;
    gateway_addr: RefObject<string>;
    max_reconnection_attempts: RefObject<number>;
    reconnection_delay: RefObject<number>;
    max_reconnection_delay: RefObject<number>;
    client_token: RefObject<string | null>;
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
    const max_reconnection_attempts = useRef<number>(5);
    const reconnection_delay = useRef<number>(1000);
    const max_reconnection_delay = useRef<number>(5000);
    const client_token = useRef<string | null>(null);
    const client = useRef<Client | null>(null);
    const current_group = useRef<Group | null>(null);
    const current_room = useRef<Room | null>(null);

    return (
        <CoreGlobalContext.Provider value = {{
            api_oauth_addr,
            gateway_addr,
            max_reconnection_attempts,
            reconnection_delay,
            max_reconnection_delay,
            client_token,
            client,
            current_group,
            current_room,
        }}>
            { children }
        </CoreGlobalContext.Provider>
    );
});