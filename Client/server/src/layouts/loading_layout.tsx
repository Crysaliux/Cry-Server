import React from "react";
import { useContext } from "react";
import { CoreGlobalContext } from "services/core";


const LoadingLayout: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    if (!context_data.loading) return null;

    return (
        <div id="loading-container">
            <div id="loading-logo">
                
            </div>
        </div>
    );
};

export default React.memo(LoadingLayout);