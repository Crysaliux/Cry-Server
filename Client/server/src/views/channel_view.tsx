import React, { useState, useEffect, useRef, useContext } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { GlobalContext } from '../services/context_manager';
import { Message } from "../components/messages";
import '../static/client_interface.css';

const ChannelView: React.FC = () => {
    const { group_id, channel_id } = useParams<{ group_id: string, channel_id: string}>();
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
    }
    const RelatedMessages = context_data.messages.filter(message => message.channel_id === channel_id);
    
    const InputReference = useRef<HTMLTextAreaElement>(null);
    const [input_content, SetInputContent] = useState<string>('');

    const IncreaseSize = () => {
        if (InputReference.current) {
            InputReference.current.style.height = 'auto';
            InputReference.current.style.height = `${InputReference.current.scrollHeight}px`
        }
    };

    useEffect(() => {
        IncreaseSize();
    }, [input_content]);

    const OnChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        SetInputContent(event.target.value);
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
                <textarea id="input-field" placeholder="Time to chat..." ref={InputReference} value={input_content} onChange={OnChange}></textarea>
                <div id="input-attachement"></div>
                <div id="input-gif"></div>
            </div>
        </>
    );
};

export default ChannelView;