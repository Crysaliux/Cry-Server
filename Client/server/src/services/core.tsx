import React, { createContext, Dispatch, ReactNode, SetStateAction, useState, memo, useRef, RefObject } from "react";
import { Client, Group, Room } from "components/index";

interface CoreGlobalProperties {
    api_oauth_addr: RefObject<string>;
    gateway_addr: RefObject<string>;
    client_token: RefObject<string | null>;
    heartbeat_addr: RefObject<string>;
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
    const heartbeat_addr = useRef<string>('localhost:8080/heartbeat/');
    const client_token = useRef<string | null>(null);
    const client = useRef<Client | null>(null);
    const current_group = useRef<Group | null>(null);
    const current_room = useRef<Room | null>(null);

    return (
        <CoreGlobalContext.Provider value = {{
            api_oauth_addr,
            gateway_addr,
            client_token,
            heartbeat_addr,
            client,
            current_group,
            current_room,
        }}>
            { children }
        </CoreGlobalContext.Provider>
    );
});