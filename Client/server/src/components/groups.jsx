import React from "react";

function Group({ id, name, icon_path, channels, owner_id }) {
    return (
        <div className="group" id={id} data-name={name} data-channels={channels} data-owner_id={owner_id}>
            <img className="groupicon" src={icon_path}></img>
        </div>
    );
}

export default Group;