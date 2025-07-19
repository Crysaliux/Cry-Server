import { useEffect, useContext } from "react";
import { CoreGlobalContext } from "./client_core";
import axios, { AxiosInstance } from "axios";
import { useNavigate } from "react-router-dom";

const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("CoreContext for oauth module can't be defined.");
    }

const ValidationRequest: AxiosInstance = axios.create({
    baseURL: `${context_data.api_oauth_addr}`, //to be fixed
    headers: {
        "Content-Type": "application/json",
    },
});

export const Authentication = () => {
    const navigate = useNavigate();

    useEffect(() => {
        const validate_existing_client = async () => {
            //Fetching client token from local storage :3, abort if none

            try {
                const response = await ValidationRequest.get("/validate_existing_client", {
                    headers: { Authorization: `Bearer ${"TOKEN"}` },
                });
                if (response.data.status) {
                    "positive"
                } else {
                    console.error(`${response.data.response}`);
                    navigate("/LOGIN");
                }
            } catch (error) {
                console.error('Verification failed:', error);
            } finally {
                "When loaded lol"
            }
        };

    }, [navigate]);

    return "VALIDATION STATUS";
};