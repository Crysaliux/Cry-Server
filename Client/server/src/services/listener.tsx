import { useEffect, useRef, useState, Dispatch, SetStateAction, use, ReactNode, useContext, createContext, RefObject } from "react";
import { 
    Group, 
    GroupNewBody, 
    GroupUpdateBody, 

    Message, 
    MessageNewBody, 
    MessageUpdateBody, 

    Permission, 
    PermissionNewBody, 

    Role, 
    RoleNewBody, 
    RoleUpdateBody, 

    Room, 
    RoomNewBody, 
    RoomUpdateBody, 

    Space, 
    SpaceNewBody, 
    SpaceUpdateBody 
} from "components/index";
import axios, { AxiosInstance } from "axios";
import { useWorker } from "./worker";

interface GatewayResponse {
    operation: string;
    status: boolean;
    error: string | null;
    body: 
        | GroupNewBody
        | GroupUpdateBody

        | MessageNewBody
        | MessageUpdateBody

        | PermissionNewBody

        | RoleNewBody
        | RoleUpdateBody

        | RoomNewBody
        | RoomUpdateBody

        | SpaceNewBody
        | SpaceUpdateBody
}

interface ListenerProperties {
    children: ReactNode;
}

interface ListenerHatchProperties {
    SendRequest: (data: ClientRequestData) => void;
}

export const ListenerHatch = createContext<ListenerHatchProperties | undefined>(undefined);

export const RequestHatch: AxiosInstance = axios.create({
    baseURL: `${context_data.api_oauth_addr}`, //to be fixed
    headers: {
        "Content-Type": "application/json",
    },
});

export const Listener: React.FC<ListenerProperties> = ({ children }) => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
    }
    const SocketReference = useRef<WebSocket | null>(null);
    const navigate = useNavigate();
    const { setGroup, setMessage, setPermission, setRole, setRoom, setSpace } = useWorker();

    useEffect(() => {
        const socket = new WebSocket(context_data.listener_addr.current);
        SocketReference.current = socket;

        socket.onmessage = async (event: MessageEvent) => {
            try {
                const data: GatewayResponse = JSON.parse(event.data);
                switch(data.operation) {
                    case "new_group":
                        const new_group_fetched = data.body as GroupNewBody;
                        setGroup({
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
                        setMessage({
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
                        setPermission({
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
                        setRole({
                            "type": "role",
                            "group_id": new_role_fetched.group_id,
                            "name": new_role_fetched.name,
                            "color": "#FFFFFF",
                            "id": new_role_fetched.id,
                        } as Role);
                        break;

                    case "new_room":
                        const new_room_fetched = data.body as RoomNewBody;
                        setRoom({
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
                        setSpace({
                            "type": "space",
                            "group_id": new_space_fetched.group_id,
                            "creator_id": new_space_fetched.creator_id,
                            "name": new_space_fetched.name,
                            "id": new_space_fetched.id,
                        } as Space);
                        break;


                    case "update_group":
                        break

                    case "update_message":
                        break;

                    case "update_role":
                        break;

                    case "update_room":
                        break;

                    case "update_space":
                        break;

                    
                    case "delete_group":
                        break;

                    case "delete_message":
                        break;

                    case "delete_role":
                        break;

                    case "delete_room":
                        break;

                    case "delete_space":
                        break;

                    case "delete_permission":
                        break;

                    case 'contact':
                        const check_contact = context_data.contacts.some(contact => contact.id === data.id);
                        if (!check_contact) {
                            context_data.SetContacts(previous => [...previous, data as Contact]);
                        } else {
                            context_data.SetContacts(previous => previous.map((contact) => contact.id === data.id ? { ...contact, ...data as Partial<Contact> } : contact));
                        }
                        break;

                    case 'group':
                        const check_group = context_data.groups.some(group => group.id === data.id);
                        if (!check_group) {
                            context_data.SetGroups(previous => [...previous, data as Group]);
                        } else {
                            context_data.SetGroups(previous => previous.map((group) => group.id === data.id ? { ...group, ...data as Partial<Group> } : group));
                        }
                        break;

                    case 'channel':
                        const check_channel = context_data.channels.some(channel => channel.id === data.id);
                        if (!check_channel) {
                            context_data.SetChannels(previous => [...previous, data as Channel]);
                        } else {
                            context_data.SetChannels(previous => previous.map((channel) => channel.id === data.id ? { ...channel, ...data as Partial<Channel> } : channel));
                        }
                        break;

                    case 'message':
                        const check_message = context_data.messages.some(message => message.id === data.id && message.sent === true);
                        if (!check_message) {
                            context_data.SetMessages(previous => previous.map(message => message.id === data.id ? { ...message, sent: true } : message));
                        } else {
                            context_data.SetMessages(previous => previous.map(message => message.id === data.id ? { ...message, ...data as Partial<Message> } : message));
                        }
                        break;

                    case 'contact_remove':
                        const check_contact_remove = context_data.contacts.some(contact => contact.id === data.id);
                        if (check_contact_remove) {
                            context_data.SetContacts(previous => previous.filter(contact => contact.id !== data.id));
                        }
                        break;

                    case 'group_remove':
                        const check_group_remove = context_data.groups.some(group => group.id === data.id);
                        if (check_group_remove) {
                            context_data.SetGroups(previous => previous.filter(group => group.id !== data.id));
                        }
                        break;

                    case 'channel_remove':
                        const check_channel_remove = context_data.channels.some(channel => channel.id === data.id);
                        if (check_channel_remove) {
                            context_data.SetChannels(previous => previous.filter(channel => channel.id !== data.id));
                        }
                        break;

                    case 'message_remove':
                        const check_message_remove = context_data.messages.some(message => message.id === data.id);
                        if (check_message_remove) {
                            context_data.SetMessages(previous => previous.filter(message => message.id !== data.id));
                        }
                        break;

                    case 'self_create_channel':
                        const check_self_channel = context_data.channels.some(channel => channel.id === data.id);
                        if (!check_self_channel) {
                            const NewChannel: Channel = {
                                type: 'channel',
                                id: data.id,
                                creator_id: data.creator_id,
                                group_id: data.group_id,
                                name: data.name,
                            };
                            context_data.SetChannels(previous => [...previous, NewChannel as Channel]);
                            context_data.SetCurrentChannelId(data.id);
                            navigate(`/group/${data.group_id}/${data.id}`);
                        }
                        break;

                    case 'group_load_members':
                        if (context_data.current_group_id === data.id) {
                            context_data.SetCurrentGroupMembers(data.members as Member[]);
                        }
                        break;

                    case 'friend_request':
                        const check_friend_request = context_data.friend_requests.some(friend_request => friend_request.client_id === data.client_id);
                        if (!check_friend_request) {
                            context_data.SetFriendRequests(previous => [...previous, data as FriendRequest]);
                        }
                        break;

                    case 'modal_status':
                        if (!data.status) {
                            if (data.error) {
                                context_data.SetError(data.error);
                            } else{
                                context_data.SetError('Looks like our servers arent responding properly, maybe try again later');
                            }
                            context_data.current_modal_failed_attempt.current = true;
                        } else {
                            context_data.SetModalDisplayStatus(false);
                        }
                        break;

                    default:
                        console.warn(`Unknown object: ${data}`);
                }
            } catch (error) {
                console.error(`Failed to parse API data: ${error}`);
            }
        };

        socket.onopen = () => {
            console.log('Client connected');
            socket.send(JSON.stringify(context_data.client_id.current));
        };

        socket.onerror = (error) => {
            console.error(`An unexpected error has occured: ${error}`);
        };

        return () => {
            socket.close();
            console.log('Client disconnected');
        };

    }, []);

    const SendRequest = (data: ClientRequestData) => {
        if (SocketReference.current && SocketReference.current.readyState === WebSocket.OPEN) {
            try {
                SocketReference.current.send(JSON.stringify(data));
            } catch (error) {
                console.error(`Can't send data to ${context_data.listener_addr}: ${error}`);
            }
        } else {
            console.warn('Connection closed!');
            context_data.SetError('Odd, seems you cant connect to our servers, check if your internet is working or try again later');
        }
    };

    useEffect(() => {
        if (context_data.modal_submit_request) {
            SendRequest(context_data.modal_submit_request as Modal);
            //context_data.SetDisplayModal(null);
        }
    }, [context_data.modal_submit_request])


    /*
    useEffect(() => {
        if (context_data.current_group_id) {
            SendRequest({ type: 'group_request_members', id: context_data.current_group_id } as ToRequestGroupMembers);
        }
    }, [context_data.current_group_id]);

    useEffect(() => {
        if (context_data.group_to_create) {
            SendRequest(context_data.group_to_create as Group);
        }
    }, [context_data.group_to_create]);

    useEffect(() => {
        if (context_data.channel_to_create) {
            SendRequest(context_data.channel_to_create as Channel);
        }
    }, [context_data.channel_to_create]);
    */
    return (
        <ListenerHatch.Provider value={{ SendRequest }}>
            { children }
        </ListenerHatch.Provider>
    );
};