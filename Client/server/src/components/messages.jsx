import React from "react";

function Message({ id, content, client_id, client_name, client_icon_path }) {
    return (
        <div className="message" id={id} data-client_id={client_id}>
            <div className="usericon">
                <img src={client_icon_path}></img>
            </div>
            <div className="messagebody">
                <div className="messageuser names_headers">
                    {client_name}
                </div>
                <div className="content userinput">
                    {content}
                </div>
            </div>
        </div>
    );
}

export default Message;