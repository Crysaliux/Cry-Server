import { Message } from "components/index";

interface CurrentGroup {
    author_id: string;
    messages: Message[];
    last_timestamp: number;
}

export function useMessagesHandler(messages: Message[], delta: number) {
    const grouped_messages: CurrentGroup[] = [];
    let curr_group: CurrentGroup | null = null;

    for (const message of messages) {
        const tstamp = new Date(message.sent_at).getTime();

        if (!curr_group) {
            curr_group = {
                author_id: message.author_id,
                messages: [message],
                last_timestamp: tstamp,
            };
        } else {

            if (curr_group.author_id == message.author_id && tstamp - curr_group.last_timestamp < delta) {
                curr_group.messages.push(message);
                curr_group.last_timestamp = tstamp;
            } else {
                grouped_messages.push(curr_group);
                curr_group = {
                    author_id: message.author_id,
                    messages: [message],
                    last_timestamp: tstamp,
                };
            }

        }
    }

    if (curr_group) {
        grouped_messages.push(curr_group);
    }

    return grouped_messages;
};