import React, { useState, useEffect, useRef, useContext } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { GlobalContext } from 'services/global_manager';
import TextareaAutosize from "react-textarea-autosize";
import { customAlphabet } from "nanoid";
import { Message } from "components/interface/messages";
import { ListenerHatch } from "services/listener";

const ChannelView: React.FC = () => {
    const { group_id, channel_id } = useParams<{ group_id: string, channel_id: string}>();
    const listener_hatch = useContext(ListenerHatch);
    const context_data = useContext(GlobalContext);
    if (!context_data || !listener_hatch) {
        throw new Error("Context for channel_view can't be defined.");
    }
    const RelatedMessages = context_data.messages.filter(message => message.channel_id === Number(channel_id));
    const input_content = useRef<string>(''); //??????????????????????????
    const id_gen = customAlphabet('123456789', 16);

    const TargetChannel = context_data.channels.find(channel => channel.id === Number(channel_id));
    if (context_data.current_group_id !== TargetChannel?.group_id) {
        context_data.SetCurrentGroupId(TargetChannel?.group_id);
    }

    const SaveContent = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        input_content.current = event.target.value;
    };

    const SendMessage = (event: React.KeyboardEvent) => {
        if (event.key === 'Enter' && context_data.client_id.current && context_data.current_group_id && context_data.current_channel_id && context_data.client_display_name) {
            event.preventDefault();
            const NewMessage: Message = {
                type: 'message',
                id: Number(id_gen()),
                sender_id: context_data.client_id.current,
                group_id: context_data.current_group_id,
                channel_id: context_data.current_channel_id,
                sender_name: context_data.client_display_name,
                sender_icon_path: 'htttp://',
                content: input_content.current,
                unread: true,
            };
            listener_hatch.SendRequest(NewMessage); //??????????????????????
        }
    };

    return (
        <>
            <div id="messages">
                {RelatedMessages.map(message => (
                    <div className="message" key={message.id} data-group_id={group_id} data-channel_id={message.channel_id} data-sender_id={message.sender_id} data-sender_name={message.sender_name}>
                        <img src={message.sender_icon_path}></img>
                        <div className="message-container">
                            <div className="message-sender medium nocopy">{message.sender_name}</div>
                            <div className="message-content small">
                                {message.content}
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            <div id="input">
                <TextareaAutosize className="medium" id="input-field" placeholder="Time to chat..." onChange={SaveContent} onKeyDown={SendMessage}></TextareaAutosize>
                <div id="input-attachement"></div>
                <div id="input-gif"></div>
            </div>
        </>
    );
};

export default React.memo(ChannelView);