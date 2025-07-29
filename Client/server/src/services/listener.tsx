import { useEffect, useRef, useState, Dispatch, SetStateAction, use, ReactNode, useContext, createContext, RefObject } from "react";
import { io } from "socket.io-client";
import { 
    Group, 
    GroupNewBody, 
    GroupUpdateBody,
    GroupDeleteBody, 

    Message, 
    MessageNewBody, 
    MessageUpdateBody, 
    MessageDeleteBody,

    Permission, 
    PermissionNewBody, 
    PermissionDeleteBody,

    Role, 
    RoleNewBody, 
    RoleUpdateBody, 
    RoleDeleteBody,

    Room, 
    RoomNewBody, 
    RoomUpdateBody, 
    RoomDeleteBody,

    Space, 
    SpaceNewBody, 
    SpaceUpdateBody,
    SpaceDeleteBody,
} from "components/index";
import axios, { AxiosInstance } from "axios";
import { CoreGlobalContext } from "./core";
import { useObjects } from "./worker";

const context_data = useContext(CoreGlobalContext);
if (!context_data) {
    throw new Error("Can't load CoreGlobalContext for listener");
}

interface HeartbeatResponse {
    status: boolean;
    error: string | null;
    interval: number | null;
}

interface GatewayResponse {
    operation: string;
    status: boolean;
    error: string | null;
    body: 
        | GroupNewBody
        | GroupUpdateBody
        | GroupDeleteBody

        | MessageNewBody
        | MessageUpdateBody
        | MessageDeleteBody

        | PermissionNewBody
        | PermissionDeleteBody

        | RoleNewBody
        | RoleUpdateBody
        | RoleDeleteBody

        | RoomNewBody
        | RoomUpdateBody
        | RoomDeleteBody

        | SpaceNewBody
        | SpaceUpdateBody
        | SpaceDeleteBody
}

/*
Heartbeat:

"operation": "heartbeat",
"status": true,
"error": null,
"body": {
    "interval": 5000 or null
}

*/


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
    const { 
        addGroup, 
        addMessage, 
        addPermission, 
        addRole, 
        addRoom, 
        addSpace,

        updateGroup,
        updateMessage,
        updateRole,
        updateRoom,
        updateSpace,

        deleteGroup,
        deleteMessage,
        deletePermission,
        deleteRole,
        deleteRoom,
        deleteSpace,
    } = useObjects();

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


        gateway.on("new_group", (data) => {
            const new_group_fetched = data.body as GroupNewBody;
            addGroup({
                "type": "group",
                "owner_id": new_group_fetched.owner_id,
                "name": new_group_fetched.name,
                "about_group": new_group_fetched.about_group,
                "icon_url": new_group_fetched.icon_url,
                "nsfw": false,
                "id": new_group_fetched.id,

                "content_filter": false,
                "content_filter_level": "none",
            } as Group);
        });
        gateway.on("new_message", (data) => {
            const new_message_fetched = data.body as MessageNewBody;
            addMessage({
                "type": "message",
                "group_id": new_message_fetched.group_id,
                "space_id": new_message_fetched.space_id,
                "room_id": new_message_fetched.room_id,
                "author_id": new_message_fetched.author_id,
                "content": new_message_fetched.content,
                "id": new_message_fetched.id,
            } as Message);
        });
        gateway.on("new_permission", (data) => {
            const new_permission_fetched = data.body as PermissionNewBody;
            addPermission({
                "type": "permission",
                "group_id": new_permission_fetched.group_id,
                "role_id": new_permission_fetched.role_id,
                "room_id": new_permission_fetched.room_id,
                "body": new_permission_fetched.body,
                "id": new_permission_fetched.id,
            } as Permission);
        });
        gateway.on("new_role", (data) => {
            const new_role_fetched = data.body as RoleNewBody;
            addRole({
                "type": "role",
                "group_id": new_role_fetched.group_id,
                "name": new_role_fetched.name,
                "color": "#FFFFFF",
                "id": new_role_fetched.id,
            } as Role);
        });
        gateway.on("new_room", (data) => {
            const new_room_fetched = data.body as RoomNewBody;
            addRoom({
                "type": "room",
                "group_id": new_room_fetched.group_id,
                "space_id": new_room_fetched.space_id,
                "creator_id": new_room_fetched.creator_id,
                "name": new_room_fetched.name,
                "about_room": new_room_fetched.about_room,
                "nsfw": false,
                "id": new_room_fetched.id,
            } as Room);
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