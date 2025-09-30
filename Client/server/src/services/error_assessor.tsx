import React, { useContext, useRef, createContext, ReactNode, useCallback } from "react";
import { CoreGlobalContext } from "./core";
import { useLocation, useNavigate } from "react-router-dom";


interface ErrorAssessorProperties {
    children: ReactNode;
}

interface ErrorHandlerProperties {
    handle: (index: string, target: string, called_by: string) => void;
}

export const ErrorHandler = createContext<ErrorHandlerProperties | undefined>(undefined);

export const ErrorAssessor: React.FC<ErrorAssessorProperties> = ({ children }) => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }
    
    const navigate = useNavigate();
    const location = useLocation();

    const handle = (index: string, target: string, called_by: string) => {
        switch (index) {
            case "OBJECT_NON_EXISTANT":
                if (target === "client") {
                    navigate(context_data.login_path.current);
                    console.error("Critical object not found! => client");
                } else {
                    console.log(`Object not found! => ${target}`);
                }
                break;

            case "INVALID_OR_EXPIRED_SESSION_TOKEN":
                console.log(`Called by: [${called_by}] <-> Access token is either expired or invalid`);
                break;

            case "INVALID_OR_EXPIRED_REFRESH_TOKEN":
                if (!context_data.oauth_ignore.current.includes(location.pathname)) navigate(context_data.login_path.current);
                console.log(`Called by: [${called_by}] <-> Refresh token is either expired or invalid`);
                break;

            case "UNRELATED":
                //
                break;

            case "MISSING_PERMISSION":
                //
                break;

            case "USERNAME_EXISTS":
                console.warn(`Called by: [${called_by}] <-> Username already exists`);
                break;

            case "EMAIL_EXISTS":
                console.warn(`Called by: [${called_by}] <-> Email already exists`);
                break;

            case "UPDATE_FAILED":
                switch (target) {
                    case "client":
                        //
                        break;

                    case "group":
                        //
                        break;

                    case "space":
                        //
                        break;

                    case "room":
                        //
                        break;

                    case "message":
                        //
                        break;

                    case "role":
                        //
                        break;

                    case "permissions_table":
                        //
                        break;

                    default:
                        console.warn(`Called by: [${called_by}] <-> Target for {UPDATE_FAILED} error can't be processed`);
                        break;
                }
                break;
            case "DELETION_REJECTED":
                //
                break;

            case "DELETION_FAILED":
                //
                break;

            case "WRONG_REQUEST":
                //
                break;

            default:
                console.warn(`Called by: [${called_by}] <-> Error index can't be processed: ${index}`);
                break;
        };
    };


    return (
        <ErrorHandler.Provider value={{ handle }}>
            { children }
        </ErrorHandler.Provider>
    );
};