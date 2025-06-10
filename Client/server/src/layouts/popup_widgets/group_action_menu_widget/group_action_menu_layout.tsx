import React, { useContext } from "react";
import { GlobalContext } from "services/global_manager";
import GroupActionMenuView from './views/group_action_menu_view';

const GrupActionMenuLayout: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for channels_view can't be defined.");
    }

    return (
        <>
            {
                context_data.group_action_menu_display_status ?
                <div id="group-action-menu-popup-widget">
                    <GroupActionMenuView />
                </div>
                : null
            }
        </>
    );
};