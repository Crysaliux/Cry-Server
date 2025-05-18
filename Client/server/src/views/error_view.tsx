import React, { Dispatch, SetStateAction, useContext } from "react";
import { GlobalContext } from '../services/context_manager';
import '../static/client_interface.css';

interface ErrorViewProperties {
    set_error: Dispatch<SetStateAction<string | null>>;
}

const ErrorView: React.FC<ErrorViewProperties> = ({ set_error }) => {
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