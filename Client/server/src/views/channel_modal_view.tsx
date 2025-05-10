import React, { useState, Dispatch, SetStateAction } from "react";
import '../static/client_interface.css';

interface ChannelModalViewProperties {
    channel_modal_status: boolean;
    set_channel_modal_status: Dispatch<SetStateAction<boolean>>;
}

const ChannelModalView: React.FC<ChannelModalViewProperties> = ({ channel_modal_status, set_channel_modal_status }) => {

    if (channel_modal_status) {
        return (
            <>
                <div className="modal" id="channel-modal">
                    <div className="modal_input" id="channel-modal-name">
                        <div className="input_info medium nocopy">What should we call it?</div>
                        <textarea maxLength={30} className="modal_input_field short_input"></textarea>
                    </div>
                    <div className="modal_choice" id="group-modal-choice">
                        <button className="button blue small nocopy">Create Channel</button>
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