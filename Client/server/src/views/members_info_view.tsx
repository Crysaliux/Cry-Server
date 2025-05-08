import React from "react";
import { Member } from "../components/members";
import '../static/client_interface.css';

interface MembersInfoViewProperties {
    members: Member[]
}

const MembersInfoView: React.FC<MembersInfoViewProperties> = ({ members }) => {
    return (
        <>
            {members.map(member => (
                <div className="member" key={member.id} data-name={member.name} data-status={member.status}>
                    <img src={member.icon_path}></img>
                    <div className="member-username medium nocopy">{member.name}</div>
                </div>
            ))}
        </>
    );
};

export default React.memo(MembersInfoView);