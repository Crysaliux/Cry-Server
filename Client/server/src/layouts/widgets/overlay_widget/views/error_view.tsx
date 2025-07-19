import React, { Dispatch, SetStateAction, useContext } from "react";
import { GlobalContext } from 'services/client_core';

const ErrorView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for error_view can't be defined.");
    }

    return (
        <>
            {   context_data.error ?
                <>
                    <div id="error" className="border">
                        <div id="error-header" className="medium nocopy">{context_data.error}</div>
                        <div id="error-ok">
                            <button id="error-ok-button" className="button blue small nocopy" onClick={() => context_data.SetError(null)}>Ok</button>
                        </div>
                    </div>
                </> : null
            }
        </>
    );
};

export default React.memo(ErrorView);