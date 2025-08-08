import { useEffect, useContext, useRef } from "react";
import { CoreGlobalContext } from "./core";
import axios, { AxiosInstance } from "axios";
import { useNavigate } from "react-router-dom";
import { APIHatch } from "./listener";

//Fetch core global context
const context_data = useContext(CoreGlobalContext);
if (!context_data) {
    throw new Error("Can't load CoreGlobalContext for oauth");
}

export const Authentication = () => {
    const navigate = useNavigate();
    const SessionTokenReference = useRef<string | null>(null);

    useEffect(() => {
        const validate_existing_client = async () => {
            try {
                SessionTokenReference.current = localStorage.getItem("SESSION");
            } catch (error) {
                console.error("Failed to retrieve session token:", error);
                navigate("/LOGIN");
            }
            try {
                if (SessionTokenReference.current) {
                    const response = await APIHatch.get("/validate_client_session", {
                        headers: { token: SessionTokenReference.current },
                    });
                    if (response.data.status) {
                        console.log("Client session seems valid");
                    } else {
                        console.error(`Session check failed: ${response.data.response}`);
                        navigate("/LOGIN");
                    }
                }
            } catch (error) {
                console.error('Session check failed:', error);
                navigate("/LOGIN");
            }
        };

    }, [navigate]);

    const fetch_group = async () => {
        const response = await APIHatch.get("/", {
            headers: { token: SessionTokenReference.current },
        });
    };

    return "VALIDATION STATUS";
};