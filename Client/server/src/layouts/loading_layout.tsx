import React from "react";
import { useContext } from "react";
import { CoreGlobalContext } from "services/core";
import styles from "../static/loading.module.css";


const LoadingLayout: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    return (
        <div id={styles.loadingContainer}>
            <div id="loading-logo">
                
            </div>
        </div>
    );
};

export default React.memo(LoadingLayout);