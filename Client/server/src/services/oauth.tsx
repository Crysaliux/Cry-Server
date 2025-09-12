import React, { ReactNode, createContext, useContext } from "react";
import { CoreGlobalContext } from "./core";
import axios, { AxiosInstance } from "axios";

interface AuthenticationProperties {
    children: ReactNode;
}

interface AuthProperties {
    //
}

export const AuthHatch = createContext<AuthProperties | undefined>(undefined);

export const Authentication: React.FC<AuthenticationProperties> = ({ children }) => {
    //Fetch core global context
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const Authrs: AxiosInstance = axios.create({
        baseURL: `${context_data.core_server_host.current}${context_data.api_oauth_addr.current}`,
        headers: {
            "session_token": `${context_data.session_token}`,
            "Content-Type": "application/json",
        },
    });

    return (
        <AuthHatch.Provider value={{ 
            //
        }}>
            { children }
        </AuthHatch.Provider>
    );
};