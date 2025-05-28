import React, { useContext } from "react";
import { GlobalContext } from 'services/global_manager';

const MembersInfoView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for members_info_view can't be defined.");
    }
    return (
        <>
            {context_data.current_group_members.map(member => (
                <div className="member border" key={member.id} data-name={member.name} data-status={member.status}>
                    <img src={member.icon_path}></img>
                    <div className="member-username medium nocopy">{member.name}</div>
                </div>
            ))}
        </>
    );
};

export default React.memo(MembersInfoView);