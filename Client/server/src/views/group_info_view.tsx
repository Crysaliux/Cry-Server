import React, { useContext } from "react";
import { useParams } from "react-router-dom";
import { GlobalContext } from '../services/global_manager';

const GroupInfoView: React.FC = () => {
    const group_id = useParams<{ group_id: string}>();
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for group_info_view can't be defined.");
    }
    const RelatedGroup = context_data.groups.find(group => group.id === group_id);
    console.log(RelatedGroup);

    return (
        <>
            {
                RelatedGroup ?
                <div id="group-info-widget">
                    <div id="group-info-widget-banner"></div>
                    <div id="group-info-widget-name" className="medium">{RelatedGroup.name}</div>
                </div>
                : null
            }
        </>
    );
};

export default React.memo(GroupInfoView);