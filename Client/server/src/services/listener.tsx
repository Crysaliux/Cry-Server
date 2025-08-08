import { useEffect, useRef, useState, Dispatch, SetStateAction, use, ReactNode, useContext, createContext, RefObject } from "react";
import { io } from "socket.io-client";
import { Client, Group, Message,Permission, Role, Room, Space, Notification } from "components/index";
import axios, { AxiosInstance } from "axios";
import { CoreGlobalContext } from "./core";
import { useObjects } from "./worker";

const context_data = useContext(CoreGlobalContext);
if (!context_data) {
    throw new Error("Can't load CoreGlobalContext for listener");
}

type Essential<T, K extends keyof T> = Partial<T> & Required<Pick<T, K>>;

interface Basic {
    id: string;
}

interface Error {
    index: string;
    target: string;
}

interface GatewayResponse {
    status: boolean;
    body: 
        | Basic 
        | Message 
        | Essential<Message, "content" | "id">
        | Essential<Client, "username" | "nickname" | "avatar_url" | "id">
        | Notification
    error: Error;
}

interface GatewayProperties {
    sendEvent: (data: object) => void;
}

interface ListenerProperties {
    children: ReactNode;
}

export const GatewayHatch = createContext<GatewayProperties | undefined>(undefined);

export const APIHatch: AxiosInstance = axios.create({
    baseURL: `${context_data.api_hatch_addr.current}`,
    headers: {
        "Content-Type": "application/json",
    },
});

export const Listener: React.FC<ListenerProperties> = ({ children }) => {
    const gateway = io(context_data.gateway_addr.current, {
        reconnection: true,
        reconnectionAttempts: context_data.max_reconnection_attempts.current,
        reconnectionDelay: context_data.reconnection_delay.current,
        reconnectionDelayMax: context_data.max_reconnection_delay.current,
    });

    useEffect(() => {
        gateway.on("connect", () => console.log("Successfully connected to gateway"));
        gateway.on("connect_error", (error) => console.log(`Gateway connection error has occured: ${error}`));
        gateway.on("disconnect", (reason) => console.error(`Gateway disconnected: ${reason}`));
        gateway.on("reconnect", (number) => console.error(`Gateway reconnected after ${number} attempts`));
        gateway.on("reconnect_attempt", () => console.log("Attempting to reconnect to gateway..."));
        gateway.on("reconnect_failed", () => console.error("Reconnection to gateway failed, is the server dead?"));


        gateway.on("group_created", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("space_created", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("room_created", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("message_sent", (data) => {
            const body = data.body as Message;
            //to be continued...
        });
        gateway.on("role_created", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("permission_created", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });


        gateway.on("client_updated", (data) => {
            const body = data.body as Essential<Client, "username" | "nickname" | "avatar_url" | "id">;
            //to be continued...
        });
        gateway.on("group_updated", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("space_updated", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("room_updated", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("message_edited", (data) => {
            const body = data.body as Essential<Message, "content" | "id">;
            //to be continued...
        });
        gateway.on("role_updated", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });


        gateway.on("client_deleted", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("group_deleted", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("space_deleted", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("room_deleted", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("message_deleted", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("role_deleted", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });
        gateway.on("permission_deleted", (data) => {
            const body = data.body as Basic;
            //to be continued...
        });

        return () => {
            gateway.off("connect");
            gateway.off("connect_error");
            gateway.off("disconnect");
            gateway.off("reconnect");
            gateway.off("reconnect_attempt");
            gateway.off("reconnect_failed");


            gateway.off("group_created");
            gateway.off("space_created");
            gateway.off("room_created");
            gateway.off("message_sent");
            gateway.off("role_created");
            gateway.off("permission_created");


            gateway.off("client_updated");
            gateway.off("group_updated");
            gateway.off("space_updated");
            gateway.off("room_updated");
            gateway.off("message_edited");
            gateway.off("role_updated");


            gateway.off("client_deleted");
            gateway.off("group_deleted");
            gateway.off("space_deleted");
            gateway.off("room_deleted");
            gateway.off("message_deleted");
            gateway.off("role_deleted");
            gateway.off("permission_deleted");
        };

    }, []);


    const fetchRooms = async (group_id: string) => {
        const response = await APIHatch.get("/rooms", {
            headers: { token: context_data.session_token.current, group_id: group_id },
        });

        if (!response.status) {
            //Make response error handler.
            return;
        }

        //Use setRooms
    };

    const fetchMessages = async (room_id: string) => {
        const response = await APIHatch.get("/messages", {
            headers: { token: context_data.session_token.current, room_id: room_id },
        });

        if (!response.status) {
            //Make response error handler.
            return;
        }

        //Use setMessages
    };

    const fetchMembers = async (room_id: string) => {
        const response = await APIHatch.get("/members", {
            headers: { token: context_data.session_token.current, room_id: room_id },
        });

        if (!response.status) {
            //Make response error handler.
            return;
        }

        //Use setMembers
    };
    
    const sendEvent = (data: object) => {
        try {
            gateway.emit("event", data);
        } catch (error) {
            console.error("Unable to send event data, gateway connection error");
        }
    };

    return (
        <GatewayHatch.Provider value={{ sendEvent }}>
            { children }
        </GatewayHatch.Provider>
    );
};