import React, { useState, Dispatch, SetStateAction, useRef, useContext } from "react";
import { GlobalContext } from '../services/global_manager';
import { Channel } from "../components/channels";
import '../static/client_interface.css';

const ChannelModalView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
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
                context_data.SetChannelToCreate(NewChannel as Channel);
            } else {
                context_data.SetError("Unexpected application error. Group doen't exist.");
            }
        } else {
            context_data.SetError('Channel name must be specified!');
        }
    };

    return (
        <>
            {
                context_data.channel_modal_status ? 
                <>
                    <div className="modal border" id="channel-modal">
                        <div className="modal_input" id="channel-modal-name">
                            <div className="input_info medium nocopy">What should we call it?</div>
                            <textarea maxLength={30} className="modal_input_field short_input" ref={ChannelNameReference}></textarea>
                        </div>
                        <div className="modal_choice" id="channel-modal-choice">
                            <button className="button blue small nocopy" onClick={CreateChannel}>Create Channel</button>
                            <button className="button underlined small nocopy" onClick={() => context_data.SetChannelModalStatus(false)}>Cancel</button>
                        </div>
                    </div>

                    <div id="modal-blur-overlay"></div>
                </> : null
            }
        </>
    );
};

export default React.memo(ChannelModalView);