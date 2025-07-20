import React, { useContext } from "react";
import { GlobalContext } from 'services/core';

const ContactsActionBarView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for friend_name_view can't be defined.");
    }

    return (
        <>
            <button className={`button transparent pointer small nocopy`}>Pending...</button>
            <button className={`button transparent pointer small nocopy`}>Blocked</button>
        </>
    );
};

export default React.memo(ContactsActionBarView);