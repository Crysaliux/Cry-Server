import { useEffect, useRef, useState, Dispatch, SetStateAction } from "react";
import { Contact } from "components/contacts";
import { Group } from "components/groups";
import { Channel } from "components/channels";
import { Message } from "components/messages";

type SocketData = Contact | Group | Channel | Message;

export const Listener = (addr: string, set_contacts: Dispatch<SetStateAction<Contact[]>>, set_groups: Dispatch<SetStateAction<Group[]>>, set_channels: Dispatch<SetStateAction<Channel[]>>, set_messages: Dispatch<SetStateAction<Message[]>>) => {
    const socketReference = useRef<WebSocket | null>(null);

    useEffect(() => {
        const socket = new WebSocket(addr);
        socketReference.current = socket;

        socket.onmessage = (event: MessageEvent) => {
            try {
                const data: SocketData = JSON.parse(event.data);

                switch(data.type) {
                    case 'contact':
                        set_contacts((previous) => [...previous, data as Contact]);
                        break;
                    case 'group':
                        set_groups((previous) => [...previous, data as Group]);
                        break;
                    case 'channel':
                        set_channels((previous) => [...previous, data as Channel]);
                        break;
                    case 'message':
                        set_messages((previous) => [...previous, data as Message]);
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
        };

        socket.onerror = (error) => {
            console.error(`An unexpected error has occured: ${error}`);
        };

        return () => {
            socket.close();
            console.log('Client disconected');
        };
    }, [addr, set_contacts, set_groups, set_channels, set_messages]);

    const SendRequest = (data: SocketData) => {
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

    return SendRequest;
};