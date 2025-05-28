import React, { useContext, useRef } from "react";
import { useParams } from "react-router-dom";
import { GlobalContext } from 'services/global_manager';
import { Group } from "components/interface/groups";

const GroupInfoView: React.FC = () => {
    const group_id = useParams<{ group_id: string}>();
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for group_info_view can't be defined.");
    }
    const RelatedGroup = useRef<Group>(undefined);

    if (context_data.current_group_id.current) {
        RelatedGroup.current = context_data.groups.find(group => group.id === context_data.current_group_id.current);
    }

    return (
        <>
            {
                RelatedGroup.current ?
                <div id="group-info-widget">
                    <div id="group-info-widget-banner"></div>
                    <div id="group-info-widget-name" className="medium">{RelatedGroup.current.name}</div>
                </div>
                : null
            }
        </>
    );
};

export default React.memo(GroupInfoView);