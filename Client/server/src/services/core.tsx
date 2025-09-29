import React, { createContext, Dispatch, ReactNode, SetStateAction, useState, memo, useRef, RefObject } from "react";
import { Client, Group, Room } from "components/index";
import { useCookies } from "react-cookie";

interface CoreGlobalProperties {
    core_server_host: RefObject<string>;
    api_oauth_addr: RefObject<string>;
    gateway_addr: RefObject<string>;
    api_hatch_addr: RefObject<string>;
    main_path: RefObject<string>;
    login_path: RefObject<string>;
    signup_path: RefObject<string>;
    client_path: RefObject<string>;
    max_reconnection_attempts: RefObject<number>;
    max_refresh_attempts: RefObject<number>;
    reconnection_delay: RefObject<number>;
    max_reconnection_delay: RefObject<number>;
    check_for_connection_in: RefObject<number>;
    client:RefObject<Client | null>;
    current_group: RefObject<Group | null>;
    current_room: RefObject<Room | null>;
    loading: boolean;
    setLoading: Dispatch<SetStateAction<boolean>>;
    gateway_ready: boolean;
    setGatewayStatus: Dispatch<SetStateAction<boolean>>;
    access_token: string | null;
    static_access_token: RefObject<string | null>;
    setAccessToken: Dispatch<SetStateAction<string | null>>;
}

interface CoreProperties {
    children: ReactNode;
}

export const CoreGlobalContext = createContext<CoreGlobalProperties | undefined>(undefined);

export const Core: React.FC<CoreProperties> = memo(({ children }) => {
    //GLOBAL CORE PROPERTIES/REFERENCES
    const core_server_host = useRef<string>("http://localhost:8080"); //Main core's host
    const api_oauth_addr = useRef<string>("/oauth");
    const gateway_addr = useRef<string>("/gateway/socket.io");
    const api_hatch_addr = useRef<string>("/api");

    const main_path = useRef<string>("/");
    const login_path = useRef<string>("/oauth2/login");
    const signup_path = useRef<string>("/oauth2/signup");
    const client_path = useRef<string>("/dms");

    const max_reconnection_attempts = useRef<number>(5);
    const max_refresh_attempts = useRef<number>(5);
    const reconnection_delay = useRef<number>(500);
    const max_reconnection_delay = useRef<number>(5000);
    const check_for_connection_in = useRef<number>(2000);

    const client = useRef<Client | null>(null);
    const current_group = useRef<Group | null>(null);
    const current_room = useRef<Room | null>(null);
    const [loading, setLoading] = useState<boolean>(false); //Remove if useless!

    const [access_token, setAccessToken] = useState<string | null>(null);
    const [gateway_ready, setGatewayStatus] = useState<boolean>(false);
    const static_access_token = useRef<string | null>(null);

    return (
        <CoreGlobalContext.Provider value = {{
            core_server_host,
            api_oauth_addr,
            gateway_addr,
            api_hatch_addr,
            main_path,
            login_path,
            signup_path,
            client_path,
            max_reconnection_attempts,
            max_refresh_attempts,
            reconnection_delay,
            max_reconnection_delay,
            check_for_connection_in,
            client,
            current_group,
            current_room,
            loading,
            setLoading,
            gateway_ready,
            setGatewayStatus,
            access_token,
            static_access_token,
            setAccessToken,
        }}>
            { children } 
        </CoreGlobalContext.Provider>
    );
});