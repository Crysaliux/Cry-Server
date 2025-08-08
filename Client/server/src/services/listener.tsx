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
    baseURL: `${context_data.api_oauth_addr.current}`,
    headers: {
        "Content-Type": "application/json",
    },
});

export const Listener: React.FC<ListenerProperties> = ({ children }) => {
    const GatewayReference = useRef<WebSocket | null>(null);
    const HeartbeatReference = useRef<WebSocket | null>(null);

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
        gateway.on("new_space", (data) => {
            const new_space_fetched = data.body as SpaceNewBody;
            addSpace({
                "type": "space",
                "group_id": new_space_fetched.group_id,
                "creator_id": new_space_fetched.creator_id,
                "name": new_space_fetched.name,
                "id": new_space_fetched.id,
            } as Space);
        });


        gateway.on("update_group", (data) => {
            updateGroup(data.body as GroupUpdateBody);
        });
        gateway.on("update_message", (data) => {
            updateMessage(data.body as MessageUpdateBody);
        });
        gateway.on("update_role", (data) => {
            updateRole(data.body as RoleUpdateBody);
        });
        gateway.on("update_room", (data) => {
            updateRoom(data.body as RoomUpdateBody);
        });
        gateway.on("update_space", (data) => {
            updateSpace(data.body as SpaceUpdateBody);
        });


        gateway.on("delete_group", (data) => {
            deleteGroup((data.body as GroupDeleteBody).id);
        });
        gateway.on("delete_message", (data) => {
            deleteMessage((data.body as MessageDeleteBody).id);
        });
        gateway.on("delete_role", (data) => {
            deleteRole((data.body as RoleDeleteBody).id);
        });
        gateway.on("delete_room", (data) => {
            deleteRoom((data.body as RoomDeleteBody).id);
        });
        gateway.on("delete_space", (data) => {
            deleteSpace((data.body as SpaceDeleteBody).id);
        });
        gateway.on("delete_permission", (data) => {
            deletePermission((data.body as PermissionDeleteBody).id);
        });

        return () => {
            gateway.off("connect");
            gateway.off("connect_error");
            gateway.off("disconnect");
            gateway.off("reconnect");
            gateway.off("reconnect_attempt");
            gateway.off("reconnect_failed");


            gateway.off("new_group");
            gateway.off("new_message");
            gateway.off("new_permission");
            gateway.off("new_role");
            gateway.off("new_room");
            gateway.off("new_space");


            gateway.off("update_group");
            gateway.off("update_message");
            gateway.off("update_role");
            gateway.off("update_room");
            gateway.off("update_space");


            gateway.off("delete_group");
            gateway.off("delete_message");
            gateway.off("delete_role");
            gateway.off("delete_room");
            gateway.off("delete_space");
            gateway.off("delete_permission");
        };

    }, []);
    
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