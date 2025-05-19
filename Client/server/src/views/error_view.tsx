import React, { Dispatch, SetStateAction, useContext } from "react";
import { GlobalContext } from '../services/context_manager';
import '../static/client_interface.css';

const ErrorView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
    }

    if (context_data.error !== null) {
        return (
            <>
            </>
        );
    } else {
        return null;
    }
};

export default ErrorView;