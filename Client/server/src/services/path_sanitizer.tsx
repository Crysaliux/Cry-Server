import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useContext } from "react";
import { CoreGlobalContext } from "services/core";


export const PathSanitizer = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const location = useLocation();
    const navigate = useNavigate();

    useEffect(() => {
        const sanitized = location.pathname.replace("/\/\/+/g", "/");
        console.log(sanitized);
        if (sanitized !== location.pathname) navigate(context_data.main_path + sanitized);
    }, [location]);

    return null;
}; //fix this boy!