import React, { Dispatch, SetStateAction } from "react";
import '../static/client_interface.css';

interface ErrorViewProperties {
    error: string | null;
    set_error: Dispatch<SetStateAction<string | null>>;
}

const ErrorView: React.FC<ErrorViewProperties> = ({ error, set_error }) => {

    if (error !== null) {
        return (
            <>
            </>
        );
    } else {
        return null;
    }
};

export default ErrorView;