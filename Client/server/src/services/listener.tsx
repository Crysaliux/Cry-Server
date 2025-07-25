import { useEffect, useRef, useState, Dispatch, SetStateAction, use, ReactNode, useContext, createContext, RefObject } from "react";
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
import { useObjects, useHeartbeat } from "./worker";

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
    GatewayRequest: (data: object) => void;
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
    const { heartbeat_interval, setHeartbeatInterval } = useHeartbeat();

    useEffect(() => {
        if (!heartbeat_interval) { return; }

        const heartbeat_timeout = useRef<number | null>(null);
        const reconnect_interval = 5000; // milliseconds (5 seconds)
        const max_reconnect_attempts = 5;
        const reconnect_attempts = useRef<number>(0);

        const Connector = () => {
            if (reconnect_attempts.current >= max_reconnect_attempts) {
                console.error("Reached reconnect attempts limit, is server dead?...");
                return;
            }

            const gateway = new WebSocket(context_data.gateway_addr.current);
            const heartbeat = new WebSocket(context_data.heartbeat_addr.current);

            GatewayReference.current = gateway;
            HeartbeatReference.current = heartbeat;
            reconnect_attempts.current += 1;

            //Gateway websocket
            gateway.onmessage = async (event: MessageEvent) => {
                try {
                    const data: GatewayResponse = JSON.parse(event.data);
                    switch(data.operation) {
                        case "on_new_group":
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
                            break;
                    
                        case "on_new_message":
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
                            break;

                        case "on_new_permission":
                            const new_permission_fetched = data.body as PermissionNewBody;
                            addPermission({
                                "type": "permission",
                                "group_id": new_permission_fetched.group_id,
                                "role_id": new_permission_fetched.role_id,
                                "room_id": new_permission_fetched.room_id,
                                "body": new_permission_fetched.body,
                                "id": new_permission_fetched.id,
                            } as Permission);
                            break;
                    
                        case "on_new_role":
                            const new_role_fetched = data.body as RoleNewBody;
                            addRole({
                                "type": "role",
                                "group_id": new_role_fetched.group_id,
                                "name": new_role_fetched.name,
                                "color": "#FFFFFF",
                                "id": new_role_fetched.id,
                            } as Role);
                            break;

                        case "on_new_room":
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
                            break;

                        case "on_new_space":
                            const new_space_fetched = data.body as SpaceNewBody;
                            addSpace({
                                "type": "space",
                                "group_id": new_space_fetched.group_id,
                                "creator_id": new_space_fetched.creator_id,
                                "name": new_space_fetched.name,
                                "id": new_space_fetched.id,
                            } as Space);
                            break;


                        case "on_update_group":
                            updateGroup(data.body as GroupUpdateBody);
                            break

                        case "on_update_message":
                            updateMessage(data.body as MessageUpdateBody);
                            break;

                        case "on_update_role":
                            updateRole(data.body as RoleUpdateBody);
                            break;

                        case "on_update_room":
                            updateRoom(data.body as RoomUpdateBody);
                            break;

                        case "on_update_space":
                            updateSpace(data.body as SpaceUpdateBody);
                            break;

                    
                        case "on_delete_group":
                            deleteGroup((data.body as GroupDeleteBody).id);
                            break;

                        case "on_delete_message":
                            deleteMessage((data.body as MessageDeleteBody).id);
                            break;

                        case "on_delete_role":
                            deleteRole((data.body as RoleDeleteBody).id);
                            break;

                        case "on_delete_room":
                            deleteRoom((data.body as RoomDeleteBody).id);
                            break;

                        case "on_delete_space":
                            deleteSpace((data.body as SpaceDeleteBody).id);
                            break;

                        case "on_delete_permission":
                            deletePermission((data.body as PermissionDeleteBody).id);
                            break;

                        default:
                            console.warn(`Gateway received an unknown request type: ${data}`);
                    }

                } catch (error) {
                    console.error(`Failed to parse gateway request: ${error}`);
                }
            };

            //Heartbeat websocket
            heartbeat.onmessage = async (event: MessageEvent) => {
                try {
                    const data: HeartbeatResponse = JSON.parse(event.data);            
                    if ((!data.status && !data.error) || (data.status && data.error)) {
                        console.warn(`Unusual server behavior, proceeding to reconnect in ${reconnect_interval / 1000} seconds`);
                        Cleanup();
                    } else {
                        if (data.error) {
                            console.warn(`Server side error, connection might collapse, ${data.error}`);
                        }
                        if (data.interval && data.interval !== heartbeat_interval) {
                            console.log(`Switching to new heartbeat interval, ${data.interval} milliseconds => ${heartbeat_interval} milliseconds`);
                            setHeartbeatInterval(data.interval);
                        }
                        if (HeartbeatReference.current && HeartbeatReference.current.readyState === WebSocket.OPEN) {
                            try {
                                HeartbeatReference.current.send(JSON.stringify(
                                    {
                                        "status": true,
                                        "error": null,
                                    }
                                ));
                                TimeoutReset();
                            } catch (error) {
                                console.error(`Unable to send heartbeat data, proceeding to reconnect in ${reconnect_interval / 1000} seconds`);
                                Cleanup();
                            }
                        } else {
                            console.error(`Connection closed unexpectedly, proceeding to reconnect in ${reconnect_interval / 1000} seconds`);
                            Cleanup();
                        }     
                    }

                } catch (error) {
                    console.error(`Failed to parse heartbeat request: ${error}`);
                }
            };

            //Gateway
            gateway.onopen = () => {
                reconnect_attempts.current = 0;
                TimeoutReset();
                console.log('Successfully connected to gateway');
            };
            gateway.onerror = (error) => {
                console.error(`An unexpected gateway error has occured: ${error}`);
            };
            gateway.onclose = () => {
                Cleanup();
            };

            //Heartbeat
            heartbeat.onopen = () => {
                reconnect_attempts.current = 0;
                TimeoutReset();
                console.log('Successfully connected to heartbeat');
            };
            heartbeat.onerror = (error) => {
                console.error(`An unexpected heartbeat error has occured: ${error}`);
            };
            heartbeat.onclose = () => {
                Cleanup();
            };
        };

        const TimeoutReset = () => {
            if (heartbeat_timeout.current) {
                clearTimeout(heartbeat_timeout.current);
            }
            heartbeat_timeout.current = setTimeout(() => {
                if (HeartbeatReference.current && HeartbeatReference.current.readyState === WebSocket.OPEN) {
                    console.error(`Server skipped a heartbeat, proceeding to reconnect in ${reconnect_interval / 1000} seconds`);
                    Cleanup();
                }
            }, heartbeat_interval + (heartbeat_interval / 2)); // Adding a safety buffer to avoid false negtives
        };

        const Cleanup = () => {
            if (heartbeat_timeout.current) {
                clearTimeout(heartbeat_timeout.current);
                heartbeat_timeout.current = null;
            }
            if (GatewayReference.current && GatewayReference.current.readyState === WebSocket.OPEN) {
                GatewayReference.current.close();
                GatewayReference.current = null;
            }
            if (HeartbeatReference.current && HeartbeatReference.current.readyState === WebSocket.OPEN) {
                HeartbeatReference.current.close();
                HeartbeatReference.current = null;
            }
            setTimeout(Connector, 5000);
        };

        Connector();

        return () => {
            Cleanup();
        };
    }, [heartbeat_interval]);
    
    const GatewayRequest = (data: object) => {
        if (GatewayReference.current && GatewayReference.current.readyState === WebSocket.OPEN) {
            try {
                GatewayReference.current.send(JSON.stringify(data));
            } catch (error) {
                console.error("Unable to send data, connection error");
            }
        } else {
            console.warn("Connection seems closed, unable to send data");
        }
    };

    return (
        <GatewayHatch.Provider value={{ GatewayRequest }}>
            { children }
        </GatewayHatch.Provider>
    );
};