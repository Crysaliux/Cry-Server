import React, { useState, Dispatch, SetStateAction, useRef } from "react";
import { Channel } from "../components/channels";
import '../static/client_interface.css';

interface ChannelModalViewProperties {
    channel_modal_status: boolean;
    current_group_id: string | null;
    set_channel_modal_status: Dispatch<SetStateAction<boolean>>;
    set_channel_to_create: Dispatch<SetStateAction<Channel | null>>;
    set_error: Dispatch<SetStateAction<string | null>>;
}

const ChannelModalView: React.FC<ChannelModalViewProperties> = ({ channel_modal_status, current_group_id, set_channel_modal_status, set_channel_to_create, set_error }) => {
    const ChannelNameReference = useRef<HTMLTextAreaElement>(null);

    const CreateChannel = () => {
        if (ChannelNameReference.current) {
            if (current_group_id !== null) {
                const NewChannel: Channel = {
                    type: 'channel',
                    id: crypto.randomUUID(),
                    group_id: current_group_id,
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

    if (channel_modal_status) {
        return (
            <>
                <div className="modal" id="channel-modal">
                    <div className="modal_input" id="channel-modal-name">
                        <div className="input_info medium nocopy">What should we call it?</div>
                        <textarea maxLength={30} className="modal_input_field short_input" ref={ChannelNameReference}></textarea>
                    </div>
                    <div className="modal_choice" id="group-modal-choice">
                        <button className="button blue small nocopy" onClick={CreateChannel}>Create Channel</button>
                        <button className="button underlined small nocopy" onClick={() => set_channel_modal_status(false)}>Cancel</button>
                    </div>
                </div>

                <div id="modal-blur-overlay"></div>
            </>
        );
    } else {
        return null;
    }
};

export default ChannelModalView;