import React, { useContext } from "react";
import { GlobalContext } from 'services/global_manager';

const GroupActionMenuView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for group_action_menu_view can't be defined.");
    }

    return (
        <>
            <div className="group_action_menu_option">
                <div className="group_action_menu_option_name">
                    New channel
                </div>
                <div className="group_action_menu_option_icon">
                    <img></img>
                </div>
            </div>

            <div className="group_action_menu_option">
                <div className="group_action_menu_option_name">
                    Settings
                </div>
                <div className="group_action_menu_option_icon">
                    <img></img>
                </div>
            </div>
        </>
    );
};

export default React.memo(GroupActionMenuView);