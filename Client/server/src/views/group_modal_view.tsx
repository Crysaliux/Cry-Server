import React, { useState } from "react";
import '../static/client_interface.css';

interface GroupModalViewProperties {
    group_modal_status: boolean;
}

const GroupModalView: React.FC<GroupModalViewProperties> = ({ group_modal_status }) => {

    if (group_modal_status) {
        return (
            <>
            </>
        );
    } else {
        return null;
    }
};

export default GroupModalView;