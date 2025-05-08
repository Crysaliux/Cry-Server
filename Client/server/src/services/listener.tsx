import { useEffect, useRef, useState, Dispatch, SetStateAction, use } from "react";
import { Contact, ToRemoveContact } from "../components/contacts";
import { Group, ToRemoveGroup, ToLoadGroupMembers, ToRequestGroupMembers } from "../components/groups";
import { Channel, ToRemoveChannel } from "../components/channels";
import { Message, ToRemoveMessage } from "../components/messages";
import { Member } from "../components/members"

type ServerRequestData = Contact | Group | Channel | Message | Partial<Contact> | Partial<Group> | Partial<Channel> | Partial<Message> | ToRemoveContact | ToRemoveGroup | ToRemoveChannel | ToRemoveMessage | ToLoadGroupMembers;
type ClientRequestData = ToRequestGroupMembers;

export const Listener = (
    addr: string,
    contacts: Contact[],
    groups: Group[],
    channels: Channel[],
    messages: Message[],
    current_group_id: string | null,
    set_contacts: Dispatch<SetStateAction<Contact[]>>,
    set_groups: Dispatch<SetStateAction<Group[]>>,
    set_channels: Dispatch<SetStateAction<Channel[]>>,
    set_messages: Dispatch<SetStateAction<Message[]>>,
    set_current_group_members: Dispatch<SetStateAction<Member[]>>,
) => {
    const socketReference = useRef<WebSocket | null>(null);

    /*
    Objects are automatically updated upon receiving a partial instance of themselves from the API.
    CONTACT_EDIT,
    MESSAGE_EDIT,
    CHANNEL_EDIT,
    GROUP_EDIT,
    */

    useEffect(() => {
        const socket = new WebSocket(addr);
        socketReference.current = socket;

        socket.onmessage = (event: MessageEvent) => {
            try {
                const data: ServerRequestData = JSON.parse(event.data);

                switch(data.type) {
                    case 'contact':
                        const check_contact = contacts.some(contact => contact.id === data.id);
                        if (!check_contact) {
                            set_contacts(previous => [...previous, data as Contact]);
                        } else {
                            set_contacts(previous => previous.map((contact) => contact.id === data.id ? { ...contact, ...data as Partial<Contact> } : contact));
                        }
                        break;

                    case 'group':
                        const check_group = groups.some(group => group.id === data.id);
                        if (!check_group) {
                            set_groups(previous => [...previous, data as Group]);
                        } else {
                            set_groups(previous => previous.map((group) => group.id === data.id ? { ...group, ...data as Partial<Group> } : group));
                        }
                        break;

                    case 'channel':
                        const check_channel = channels.some(channel => channel.id === data.id);
                        if (!check_channel) {
                            set_channels(previous => [...previous, data as Channel]);
                        } else {
                            set_channels(previous => previous.map((channel) => channel.id === data.id ? { ...channel, ...data as Partial<Channel> } : channel));
                        }
                        break;

                    case 'message':
                        const check_message = messages.some(message => message.id === data.id);
                        if (!check_message) {
                            set_messages(previous => [...previous, data as Message]);
                        } else {
                            set_messages(previous => previous.map(message => message.id === data.id ? { ...message, ...data as Partial<Message> } : message));
                        }
                        break;

                    case 'contact_remove':
                        const check_contact_remove = contacts.some(contact => contact.id === data.id);
                        if (check_contact_remove) {
                            set_contacts(previous => previous.filter(contact => contact.id !== data.id));
                        }
                        break;

                    case 'group_remove':
                        const check_group_remove = groups.some(group => group.id === data.id);
                        if (check_group_remove) {
                            set_groups(previous => previous.filter(group => group.id !== data.id));
                        }
                        break;

                    case 'channel_remove':
                        const check_channel_remove = channels.some(channel => channel.id === data.id);
                        if (check_channel_remove) {
                            set_channels(previous => previous.filter(channel => channel.id !== data.id));
                        }
                        break;

                    case 'message_remove':
                        const check_message_remove = messages.some(message => message.id === data.id);
                        if (check_message_remove) {
                            set_messages(previous => previous.filter(message => message.id !== data.id));
                        }
                        break;

                    case 'group_load_members':
                        if (current_group_id === data.id) {
                            set_current_group_members(data.members as Member[]);
                        }

                    default:
                        console.warn(`Unknown object: ${data}`);
                }
            } catch (error) {
                console.error(`Failed to parse API data: ${error}`);
            }
        };

        socket.onopen = () => {
            console.log('Client connected');
        };

        socket.onerror = (error) => {
            console.error(`An unexpected error has occured: ${error}`);
        };

        return () => {
            socket.close();
            console.log('Client disconected');
        };

    }, []);

    const SendRequest = (data: ClientRequestData) => {
        if (socketReference.current && socketReference.current.readyState === WebSocket.OPEN) {
            try {
                socketReference.current.send(JSON.stringify(data));
            } catch (error) {
                console.error(`Can't send data to ${addr}: ${error}`);
            }
        } else {
          console.warn('Connection closed!');
        }
    };

    useEffect(() => {
        if (current_group_id !== null) {
            SendRequest({ type: 'group_request_members', id: current_group_id } as ToRequestGroupMembers);
        }
    }, [current_group_id]);

    return SendRequest;
};