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

interface Heartbeat {
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


        | Heartbeat
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

export const RequestHatch: AxiosInstance = axios.create({
    baseURL: `${context_data.api_oauth_addr.current}`,
    headers: {
        "Content-Type": "application/json",
    },
});

export const Listener: React.FC<ListenerProperties> = ({ children }) => {
    const SocketReference = useRef<WebSocket | null>(null);
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
        const max_reconnect_attempts = 5;
        const reconnect_attempts = useRef<number>(0);
        const safety_buffer = 5000;

        const GatewayConnector = () => {
            if (reconnect_attempts.current >= max_reconnect_attempts) {
                console.error("Reached reconnect attempts limit, is server dead?...");
                return;
            }

            const socket = new WebSocket(context_data.gateway_addr.current);
            SocketReference.current = socket;
            reconnect_attempts.current += 1;

            socket.onmessage = async (event: MessageEvent) => {
                try {
                    const data: GatewayResponse = JSON.parse(event.data);
                    switch(data.operation) {
                        case "new_group":
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
                    
                        case "new_message":
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

                        case "new_permission":
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
                    
                        case "new_role":
                            const new_role_fetched = data.body as RoleNewBody;
                            addRole({
                                "type": "role",
                                "group_id": new_role_fetched.group_id,
                                "name": new_role_fetched.name,
                                "color": "#FFFFFF",
                                "id": new_role_fetched.id,
                            } as Role);
                            break;

                        case "new_room":
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

                        case "new_space":
                            const new_space_fetched = data.body as SpaceNewBody;
                            addSpace({
                                "type": "space",
                                "group_id": new_space_fetched.group_id,
                                "creator_id": new_space_fetched.creator_id,
                                "name": new_space_fetched.name,
                                "id": new_space_fetched.id,
                            } as Space);
                            break;


                        case "update_group":
                            updateGroup(data.body as GroupUpdateBody);
                            break

                        case "update_message":
                            updateMessage(data.body as MessageUpdateBody);
                            break;

                        case "update_role":
                            updateRole(data.body as RoleUpdateBody);
                            break;

                        case "update_room":
                            updateRoom(data.body as RoomUpdateBody);
                            break;

                        case "update_space":
                            updateSpace(data.body as SpaceUpdateBody);
                            break;

                    
                        case "delete_group":
                            deleteGroup((data.body as GroupDeleteBody).id);
                            break;

                        case "delete_message":
                            deleteMessage((data.body as MessageDeleteBody).id);
                            break;

                        case "delete_role":
                            deleteRole((data.body as RoleDeleteBody).id);
                            break;

                        case "delete_room":
                            deleteRoom((data.body as RoomDeleteBody).id);
                            break;

                        case "delete_space":
                            deleteSpace((data.body as SpaceDeleteBody).id);
                            break;

                        case "delete_permission":
                            deletePermission((data.body as PermissionDeleteBody).id);
                            break;

                    
                        case "heartbeat":
                            const heartbeat_fetched = data.body as Heartbeat;
                            if ((!data.status && !data.error) || (data.status && data.error)) {
                                console.warn("Unusual server behavior, connection closed automatically");
                                Cleanup();
                            } else {
                                if (data.error) {
                                    console.warn(`Server side error, connection might collapse, ${data.error}`);
                                }
                                if (heartbeat_fetched.interval && heartbeat_fetched.interval !== heartbeat_interval) {
                                    console.log(`Switching to new heartbeat interval, ${heartbeat_fetched.interval} milliseconds => ${heartbeat_interval} milliseconds`);
                                    setHeartbeatInterval(heartbeat_fetched.interval);
                                } else {
                                    TimeoutReset();
                                    GatewayRequest({
                                        "type": "websocket",
                                        "status": true,
                                        "error": null, //true and null for now only, will change this later.
                                    });
                                }
                            }
                            break;

                        default:
                            console.warn(`Unknown request: ${data}`);
                    }
                } catch (error) {
                    console.error(`Failed to parse Gateway request: ${error}`);
                }
            };

            socket.onopen = () => {
                reconnect_attempts.current = 0;
                TimeoutReset();
                console.log('Successfully connected to Gateway');
            };

            socket.onerror = (error) => {
                console.error(`An unexpected error has occured: ${error}`);
            };

            socket.onclose = () => {
                Cleanup();
            };
        };

        const GatewayRequest = (data: object) => {
            if (SocketReference.current && SocketReference.current.readyState === WebSocket.OPEN) {
                try {
                    SocketReference.current.send(JSON.stringify(data));
                } catch (error) {
                    console.error("Unable to send data, connection error");
                }
            } else {
                console.warn("Connection closed, unable to send data");
                //context_data.SetError('Odd, seems you cant connect to our servers, check if your internet is working or try again later');
            }
        };

        const TimeoutReset = () => {
            if (heartbeat_timeout.current) {
                clearTimeout(heartbeat_timeout.current);
            }
            heartbeat_timeout.current = setTimeout(() => {
                if (SocketReference.current && SocketReference.current.readyState === WebSocket.OPEN) {
                    SocketReference.current.close();
                    Cleanup();
                }
            }, heartbeat_interval + safety_buffer);
        };

        const Cleanup = () => {
            if (heartbeat_timeout.current) {
                clearTimeout(heartbeat_timeout.current);
                heartbeat_timeout.current = null;
            }
            if (SocketReference.current && SocketReference.current.readyState === WebSocket.OPEN) {
                SocketReference.current.close();
                SocketReference.current = null;
            }
            setTimeout(GatewayConnector, 5000);
        };

        GatewayConnector();

        return () => {
            Cleanup();
        };
    }, [heartbeat_interval]);
                                    //gotta think about this one.
    return (
        <GatewayHatch.Provider value={{ GatewayRequest }}>
            { children }
        </GatewayHatch.Provider>
    );
};