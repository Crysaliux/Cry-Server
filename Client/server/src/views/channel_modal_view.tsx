import React, { useState, Dispatch, SetStateAction, useRef, useContext } from "react";
import { GlobalContext } from '../services/context_manager';
import { Channel } from "../components/channels";
import '../static/client_interface.css';

interface ChannelModalViewProperties {
    set_channel_modal_status: Dispatch<SetStateAction<boolean>>;
    set_channel_to_create: Dispatch<SetStateAction<Channel | null>>;
    set_error: Dispatch<SetStateAction<string | null>>;
}

const ChannelModalView: React.FC<ChannelModalViewProperties> = ({ set_channel_modal_status, set_channel_to_create, set_error }) => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
    }
    if (!context_data.channel_modal_status) {
        return null;
    }
    const ChannelNameReference = useRef<HTMLTextAreaElement>(null);

    const CreateChannel = () => {
        if (ChannelNameReference.current) {
            if (context_data.current_group_id !== null) {
                const NewChannel: Channel = {
                    type: 'channel',
                    id: parseInt(crypto.randomUUID().replace(/\D/g, ''), 10),
                    creator_id: 5555, //To be implemented!
                    group_id: context_data.current_group_id,
                    name: ChannelNameReference.current.value
                };
                set_channel_to_create(NewChannel);
            } else {
                set_error("Unexpected application error. Group doen't exist.");
            }
        } else {
            set_error('Channel name must be specified!');
        }
    };

    return (
        <>
            <div className="modal" id="channel-modal">
                <div className="modal_input" id="channel-modal-name">
                    <div className="input_info medium nocopy">What should we call it?</div>
                    <textarea maxLength={30} className="modal_input_field short_input" ref={ChannelNameReference}></textarea>
                </div>
                <div className="modal_choice" id="channel-modal-choice">
                    <button className="button blue small nocopy" onClick={CreateChannel}>Create Channel</button>
                    <button className="button underlined small nocopy" onClick={() => set_channel_modal_status(false)}>Cancel</button>
                </div>
            </div>

            <div id="modal-blur-overlay"></div>
        </>
    );
};

export default ChannelModalView;