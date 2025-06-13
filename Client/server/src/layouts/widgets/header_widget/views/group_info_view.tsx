import React, { useContext, useRef } from "react";
import { GlobalContext } from 'services/global_manager';
import { Group } from "components/interface/groups";

const GroupInfoView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for group_info_view can't be defined.");
    }
    const RelatedGroup = useRef<Group | undefined>(undefined);

    if (context_data.current_group_id) {
        RelatedGroup.current = context_data.groups.find(group => group.id === context_data.current_group_id);
    }

    const HandleGroupActionMenuRightClick = () => {
        if (!context_data.group_action_menu_display_status) {
            context_data.SetGroupActionMenuDisplayStatus(true);
        } else {
            context_data.SetGroupActionMenuDisplayStatus(false);
        }
    };

    const HandleGroupActionMenuLeftClick = (event: React.MouseEvent<HTMLDivElement>) => {
        event.preventDefault();
        if (!context_data.group_action_menu_display_status) {
            context_data.SetGroupActionMenuDisplayStatus(true);
        }
    };

    return (
        <>
            {
                RelatedGroup.current ?
                <div id="group-info-widget" className="nocopy" onClick={HandleGroupActionMenuRightClick} onContextMenu={HandleGroupActionMenuLeftClick}>
                    <div id="group-info-widget-name" className="big">{RelatedGroup.current.name}</div>
                </div>
                : null
            }
        </>
    );
};

export default React.memo(GroupInfoView);