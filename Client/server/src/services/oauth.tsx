import { useEffect, useContext } from "react";
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

    useEffect(() => {
        const validate_existing_client = async () => {
            //Fetching client token from local storage :3, abort if none

            try {
                const response = await APIHatch.get("/validate_client_session", {
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