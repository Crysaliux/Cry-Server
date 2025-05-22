import { useEffect, useRef, useState, Dispatch, SetStateAction, use, ReactNode, useContext } from "react";
import { GlobalContext } from '../services/global_manager';
import { Contact, ToRemoveContact } from "../components/interface/contacts";
import { Group, ToRemoveGroup, ToLoadGroupMembers, ToRequestGroupMembers } from "../components/interface/groups";
import { Channel, ToRemoveChannel } from "../components/interface/channels";
import { Message, ToRemoveMessage } from "../components/interface/messages";
import { Member } from "../components/interface/members";
import { Modal, ModalStatus } from "../components/overlay/modal";

type ServerRequestData = Contact | Group | Channel | Message | Partial<Contact> | Partial<Group> | Partial<Channel> | Partial<Message> | ToRemoveContact | ToRemoveGroup | ToRemoveChannel | ToRemoveMessage | ToLoadGroupMembers | ModalStatus;
type ClientRequestData = ToRequestGroupMembers | Modal;

interface ListenerProperties {
    children: ReactNode;
}

export const Listener: React.FC<ListenerProperties> = ({ children }) => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
    }
    const socketReference = useRef<WebSocket | null>(null);

    /*
    Objects are automatically updated upon receiving a partial instance of themselves from the API.
    CONTACT_EDIT,
    MESSAGE_EDIT,
    CHANNEL_EDIT,
    GROUP_EDIT,
    */

    useEffect(() => {
        var addr = 'ws://localhost:8080/client/api'; //Default
        if (context_data.listener_addr) {
            addr = context_data.listener_addr
        }
        const socket = new WebSocket(addr);
        socketReference.current = socket;

        socket.onmessage = async (event: MessageEvent) => {
            try {
                const data: ServerRequestData = JSON.parse(event.data);
                switch(data.type) {
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
                        const check_message = context_data.messages.some(message => message.id === data.id);
                        if (!check_message) {
                            context_data.SetMessages(previous => [...previous, data as Message]);
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

                    case 'group_load_members':
                        if (context_data.current_group_id === data.id) {
                            context_data.SetCurrentGroupMembers(data.members as Member[]);
                        }
                        break;

                    case 'modal_status':
                        if (!data.status) {
                            context_data.SetError("Application error. Couldn't create object");
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
            socket.send(JSON.stringify(context_data.client_id));
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
        if (socketReference.current && socketReference.current.readyState === WebSocket.OPEN) {
            try {
                socketReference.current.send(JSON.stringify(data));
            } catch (error) {
                console.error(`Can't send data to ${context_data.listener_addr}: ${error}`);
            }
        } else {
          console.warn('Connection closed!');
        }
    };

    useEffect(() => {
        if (context_data.modal_submit_request) {
            SendRequest(context_data.modal_submit_request as Modal);
            context_data.SetDisplayModal(null);
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
    return children;
};