import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Group } from "../components/groups";
import { Channel } from "../components/channels";
import { Message } from "../components/messages";
import { ListFormat } from "typescript";

interface GroupViewProperties {
    message_edit: typeof Liste
}

const GroupView: React.FC = () => {
    const id = useParams<{id: string}>();
    const navigate = useNavigate();
    
    const ChannelHandler = (name: string) => {
        const NewChannel: Channel = {
            type: 'channel',
            id: crypto.randomUUID(),
            name: name
        };
        SendRequest(NewChannel);
    };
};