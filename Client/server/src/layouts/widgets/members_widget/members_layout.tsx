import React from "react";
import MembersInfoView from './views/members_info_view';

const MembersLayout: React.FC = () => {
    return (
        <div id="members-contact-widget" className="widget">
            <MembersInfoView />
        </div>
    );
};

export default React.memo(MembersLayout);