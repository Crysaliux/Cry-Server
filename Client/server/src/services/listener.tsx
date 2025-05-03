import React from "react";
import { useEffect, useRef, useState } from "react";
import { Group } from "../components/groups";
import { Channel } from "../components/channels";
import { Message } from "../components/messages";

type SocketData = Group | Channel | Message

export const Listener = (addr: string) => {
    const [groups, SetGroups] = useState<Group[]>([]);
    const [channels, SetChannels] = useState<Channel[]>([]);
    const [messages, SetMessages] = useState<Message[]>([]);
    const socketReference = useRef<WebSocket | null>(null);

    useEffect(() => {
        const socket = new WebSocket(addr);
        socketReference.current = socket;

        socket.onmessage = (event: MessageEvent) => {
            try {
                const data: SocketData = JSON.parse(event.data);

                switch(data.type) {
                    case 'group':
                        SetGroups((previous) => [...previous, data as Group]);
                        break;
                    case 'channel':
                        SetChannels((previous) => [...previous, data as Channel]);
                        break;
                    case 'message':
                        SetMessages((previous) => [...previous, data as Message]);
                        break;
                    default:
                        console.warn(`Unknown object: ${data}`);
                }
            } catch (error) {
                console.error(`Failed to parse API data: ${error}`)
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
    }, [addr]);

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

    return { groups, channels, messages, SendRequest }
};