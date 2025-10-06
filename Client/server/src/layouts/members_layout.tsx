import React, { useContext } from "react";
import { CoreGlobalContext } from "services/core";
import { useMembers } from "services/worker";
import styles from "../static/group.module.css";

const MembersLayout: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for room_layout module");
    }

    const members = useMembers();
    const members_array = Object.values(members);

    return (
        <div id={styles.members}>

            {members_array.map(member => (
                <div className={styles.member} key={member.id}>
                    <div className={styles.memberAvatar}>
                        <div className={styles.onlineStatus}>
                            <div className={styles.onlineStatusMarker}></div>
                        </div>
                    </div>
                    <div className={styles.nickname}>Nickname</div>
                </div>
            ))}
                
        </div>
    )
};

export default React.memo(MembersLayout);