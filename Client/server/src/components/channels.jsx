import React from "react";

function Channel({ id, name }) {
    return (
        <div className="channel names_headers" id={id} data-name={name}># - {name}</div>
    );
}

export default Channel;