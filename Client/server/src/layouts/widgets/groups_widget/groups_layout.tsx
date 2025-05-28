import React from "react";
import ActionBarView from './views/action_bar_view';
import GroupsView from './views/groups_view';

const GroupsLayout: React.FC = () => {
    return (
        <div id="groups-widget" className="widget">
            <GroupsView />
            <div id="groups-widget-action-bar">
                <ActionBarView />
            </div>
        </div>
    );
};

export default React.memo(GroupsLayout);