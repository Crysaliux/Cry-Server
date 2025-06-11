import React, { useContext, useEffect, useState } from "react";
import { GlobalContext } from "services/global_manager";
import GroupActionMenuView from './views/group_action_menu_view';

interface CursorPosition {
    cursor_x: number;
    cursor_y: number;
}

const GroupActionMenuLayout: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for channels_view can't be defined.");
    }

    return (
        <>
            {
                context_data.group_action_menu_display_status ?
                <div id="group-action-menu-popup-widget" className="popup-widget">
                    <GroupActionMenuView />
                </div>
                : null
            }
        </>
    );
};

export default React.memo(GroupActionMenuLayout);