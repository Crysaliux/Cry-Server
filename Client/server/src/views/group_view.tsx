import React, { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Listener } from "../services/listener";
import { Group } from "../components/groups";
import { Channel } from "../components/channels";
import { Message } from "../components/messages";
import { ListFormat } from "typescript";

interface GroupViewChannels {
    channels: ListFormat
}

const GroupView: React.FC = () => {
    const id = useParams<{id: string}>();
    const [channels, SetChannels]
    const navigate = useNavigate();

    useEffect
    
    const ChannelHandler = (name: string) => {
        const NewChannel: Channel = {
            type: 'channel',
            id: crypto.randomUUID(),
            name: name
        };
        SendRequest(NewChannel);
    };


};