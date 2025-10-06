import React, { useContext } from "react";
import { 
    useMessages, 
} from "services/worker";
import { CoreGlobalContext } from "services/core";
import { useMessagesHandler } from "services/handlers/messages_handler";
import { Message } from "components";
import styles from "../static/group.module.css";
import TextareaAutosize from "react-textarea-autosize";
import MembersLayout from "layouts/members_layout";


function useAdditionalMessages(adms: Message[]) {
    adms.shift();
    return (
        <>
            {adms.map(adm => (
                <div className={styles.additionalMessage} key={adm.id}>
                    <div className={styles.buffer}></div>
                    <div className={styles.body}>
                        <div className={styles.content}>
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
    const messages_array = Object.values(messages); //context_data.message_sent_delta.current
    const grouped_messages = useMessagesHandler(messages_array, 20);

    return (
        <>
            <div id={styles.chat}>
                <div id={styles.messages}>
                    {grouped_messages.map(grouped_message => (
                        <>
                            <div className={styles.message} key={grouped_message.messages[0].id}>
                                <div className={styles.avatar}></div>
                                <div className={styles.body}>
                                    <div className={styles.nickname}>{grouped_message.messages[0].nickname}</div>
                                    <div className={styles.content}>
                                        {grouped_message.messages[0].content}
                                    </div>
                                </div>
                            </div>

                            {useAdditionalMessages(grouped_message.messages)};
                        </>
                    ))}
                </div>

                <div id={styles.chatArea}>
                    <div id={styles.attachement}></div>
                    <TextareaAutosize autoFocus id={styles.chatBar}></TextareaAutosize>
                </div>

            </div>
            <MembersLayout />
        </>
    );
};

export default React.memo(RoomLayout);