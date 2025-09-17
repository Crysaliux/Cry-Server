import { NavigateFunction, useNavigate } from "react-router-dom";

export const ErrorHandler = (index: string, target: string, navigate: NavigateFunction) => {
    switch (index) {
        case "OBJECT_NON_EXISTANT":
            if (target === "client") {
                try {
                    navigate("/login") // unnnecessary.
                } catch(error) {
                    console.error(`Failed to navigate to /login: ${error}`);
                }
            }
            break;
        case "INVALID_OR_EXPIRED_SESSION_TOKEN":
            console.log("INVALID_OR_EXPIRED_SESSION_TOKEN"); //test
            break;
        case "UNRELATED":
            //
            break;
        case "MISSING_PERMISSION":
            //
            break;
        case "USERNAME_EXISTS":
            console.warn("Username already exists");
            break;
        case "EMAIL_EXISTS":
            console.warn("Email already exists");
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
                    console.warn("Target for [UPDATE_FAILED] error can't be processed");
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
            console.warn(`Error index can't be processed: ${index}`);
            break;
    }
};