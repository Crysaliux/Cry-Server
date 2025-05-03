import React from "react";
import { Listener } from "../services/listener";
import { Group } from "../components/groups";
import { Channel } from "../components/channels";
import { Message } from "../components/messages";

const GroupView: React.FC = () =>  {
    const { groups, channels, messages, SendRequest } = Listener("ws://somehost/listener");

    const GroupHandler = (owner_id: number | string, icon_path: string, name: string, desc: string) => {
        const NewGroup: Group = {
            type: 'group',
            id: crypto.randomUUID(),
            owner_id: owner_id,
            icon_path: icon_path,
            name: name,
            desc: desc
        };
        SendRequest(NewGroup);
    };

    const ChannelHandler = (name: string) => {
        const NewChannel: Channel = {
            type: 'channel',
            id: crypto.randomUUID(),
            name: name
        };
        SendRequest(NewChannel);
    };

    const MessageHandler = (sender_id: number | string, sender_name: string, sender_icon_path: string, content: string) => {
        const NewMessage: Message = {
            type: 'message',
            id: crypto.randomUUID(),
            sender_id: sender_id,
            sender_name: sender_name,
            sender_icon_path: sender_icon_path,
            content: content,
        };
        SendRequest(NewMessage);
    };
    
    return (
        <div id="container">
            <div id="overlays">
                <div id="client-overlay"></div>
                <div id="modal-overlay"></div>
            </div>
            <div id="widgets">
                <div id="header-widget" className="widget"></div>
                <div id="groups-widget" className="widget"></div>
                <div id="channels-contacts-widget" className="widget"></div>
                <div id="chat-widget" className="widget"></div>
                <div id="members-contact-widget" className="widget"></div>
                <div id="member-info-popup-widget" className="popup-widget"></div>
                <div id="client-info-popup-widget" className="popup-widget"></div>
                <div id="channel-settings-popup-widget" className="popup-widget"></div>
                <div id="group-settings-popup-widget" className="popup-widget"></div>
            </div>
        </div>
    );

};