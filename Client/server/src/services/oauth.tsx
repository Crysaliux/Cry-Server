import { useEffect, useContext, useRef } from "react";
import { CoreGlobalContext } from "./core";
import axios, { AxiosInstance } from "axios";
import { useLocation, useNavigate } from "react-router-dom";
import { APIHatch } from "./listener";

//Fetch core global context
const context_data = useContext(CoreGlobalContext);
if (!context_data) {
    throw new Error("Can't load CoreGlobalContext for oauth");
}


export const Authentication = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const SessionTokenReference = useRef<string | null>(null);

    useEffect(() => {
        const fetch_group = async (id: string, room_id: string) => {
            await __fetch_group(id, room_id);
        };

        const parts = location.pathname.split("/").filter(Boolean);
        if (parts.length < 1) return;

        const [group_id, room_id] = parts;
        if (group_id) fetch_group(group_id, room_id);

    }, [location]);

    const __fetch_group = async (id: string, room_id: string) => {
        const response = await APIHatch.get("/fetch_group", {
            headers: { session_token: SessionTokenReference.current, id: id, room_id: room_id },
        });
    };
};

/*
To do list:
- add session token handlers
- add proper __fetch... handlers
- 
*/