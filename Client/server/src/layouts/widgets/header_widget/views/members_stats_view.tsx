import React, { useContext } from "react";
import { GlobalContext } from 'services/core';

const MembersStatsView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for members_stats_view can't be defined.");
    }

    return (null);
};

export default React.memo(MembersStatsView);