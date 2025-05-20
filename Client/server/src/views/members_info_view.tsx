import React, { useContext } from "react";
import { GlobalContext } from '../services/global_manager';
import '../static/client_interface.css';

const MembersInfoView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
    }
    return (
        <>
            {context_data.current_group_members.map(member => (
                <div className="member" key={member.id} data-name={member.name} data-status={member.status}>
                    <img src={member.icon_path}></img>
                    <div className="member-username medium nocopy">{member.name}</div>
                </div>
            ))}
        </>
    );
};

export default React.memo(MembersInfoView);