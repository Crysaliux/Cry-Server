import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Listener } from "../services/listener";
import { Group } from "../components/groups";
import { Channel } from "../components/channels";
import { Message } from "../components/messages";

/*
Total redirect.
Group + Channels + Chat displayed.
*/

const ChatView: React.FC = () =>  {
    const { group_id, channel_id } = useParams<{ group_id: string | undefined; channel_id: string | undefined}>();
    const { groups, channels, messages, SendRequest } = Listener("ws://somehost/listener", group_id, channel_id);
    const navigate = useNavigate();

    if (!group_id) {
        navigate('/', { replace: true });
        return null;
    }

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
                <div id="groups-widget" className="widget">
                    {groups.map((group) => (
                        <div className="group" key={group.id} data-owner_id={group.owner_id} data-desc={group.desc}>
                            <img src={group.icon_path}></img>
                        </div>
                    ))}
                </div>
                <div id="channels-contacts-widget" className="widget">
                    {channels.map((channel) => (
                        <div className="channel medium nocopy" key={channel.id} data-name={channel.name}># {channel.name}</div>
                    ))}
                </div>
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