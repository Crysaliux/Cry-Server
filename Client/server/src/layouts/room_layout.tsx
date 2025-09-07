import React, { useContext } from "react";
import { 
    useMessages, 
} from "services/worker";
import { CoreGlobalContext } from "services/core";
import { useMessagesHandler } from "services/handlers/messages_handler";
import { Message } from "components";


function useAdditionalMessages(adms: Message[]) {
    adms.shift();
    return (
        <>
            {adms.map(adm => (
                <div className="additional_message" key={adm.id}>
                    <div className="buffer"></div>
                    <div className="body">
                        <div className="content">
                            {adm.content}
                        </div>
                    </div>
                </div>
            ))}
        </>
    );
};

const RoomLayout: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for room_layout module");
    }

    const messages = useMessages();
    const messages_array = Object.values(messages);
    const grouped_messages = useMessagesHandler(messages_array, context_data.message_sent_delta.current);

    return (
        <div id="chat">
            <div id="messages">
                {grouped_messages.map(grouped_message => (
                    <>
                        <div className="message" key={grouped_message.messages[0].id}>
                            <div className="avatar"></div>
                            <div className="body">
                                <div className="nickname">{grouped_message.messages[0].nickname}</div>
                                <div className="content">
                                    {grouped_message.messages[0].content}
                                </div>
                            </div>
                        </div>

                        {useAdditionalMessages(grouped_message.messages)};
                    </>
                ))}
            </div>

            <div id="chatarea">
                <div id="attachement"></div>
                <textarea autoFocus id="chatbar"></textarea>
            </div>

        </div>
    );
};

export default React.memo(RoomLayout);