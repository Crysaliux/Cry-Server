import React, { ReactNode, createContext, useContext, useCallback } from "react";
import { CoreGlobalContext } from "./core";
import axios, { AxiosInstance } from "axios";
import { useNavigate } from "react-router-dom";
import { ErrorHandler } from "./handlers/error_handler";
import { z } from "zod";
import { withCookies } from "react-cookie";


const ErrorSchema = z.object({
    index: z.string(),
    target: z.string(),
});

const AccessSchema = z.object({
    access_token: z.string(),
});

const ResponseSchema = z.object({ //hbb - handled by backend
    status: z.boolean(),
    body: z.union([
        AccessSchema,
    ]).nullable(),
    error: ErrorSchema.nullable(),
});

interface AuthenticationProperties {
    children: ReactNode;
}

interface AuthProperties {
    refresh: () => Promise<boolean>;
    login: (email: string, password: string) => Promise<boolean>;
    signup: (username: string, email: string, password: string, date_of_birth: string) => Promise<boolean>;
}

export const AuthHatch = createContext<AuthProperties | undefined>(undefined);

export const Authentication: React.FC<AuthenticationProperties> = ({ children }) => {
    //Fetch core global context
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const navigate = useNavigate();

    const Authrs: AxiosInstance = axios.create({
        baseURL: `${context_data.core_server_host.current}${context_data.api_oauth_addr.current}`,
        headers: {
            "Content-Type": "application/json",
        },
    });


    const __refresh = useCallback(async () => {
        const response = await Authrs.post("/refresh_session", {}, {
            withCredentials: true,
        });

        const parsed_response = ResponseSchema.safeParse(response.data);
        
        if (!parsed_response.success) {
            navigate(context_data.login_path.current);
            console.error(`Refresh, can't process server response: ${parsed_response.data}`);
            return false;
        }
        
        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                navigate(context_data.login_path.current);
                console.error(`Can't display exact error, refresh failed: ${error.error.issues}`);
                return false;
            }
            if (!error.data.index) {
                navigate(context_data.login_path.current);
                console.error("Can't display exact error, no index provided");
                return false;
            }
        
            ErrorHandler(error.data.index, error.data.target, navigate); //fix it. Display only.
            return false;
        }
        
        const actual = AccessSchema.safeParse(parsed_response.data.body);
        
        if (!actual.success) {
            navigate(context_data.login_path.current);
            console.error(`Refresh failed, can't process server response: ${parsed_response.data.body}`);
            return false;
        }
                
        const refresh: z.infer<typeof AccessSchema> = actual.data;

        context_data.static_access_token.current = refresh.access_token;
        context_data.setAccessToken(refresh.access_token);
        return true;
    }, []);

    const login = useCallback(async (email: string, password: string) => {
        const response = await Authrs.post("/login", {
            email: email, password: password,
        }, {
            withCredentials: true,
        });

        const parsed_response = ResponseSchema.safeParse(response.data);
        
        if (!parsed_response.success) {
            console.error(`Login failed, can't process server response: ${parsed_response.data}`);
            return false;
        }
        
        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, login failed: ${error.error.issues}`);
                return false;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return false;
            }
        
            ErrorHandler(error.data.index, error.data.target, navigate); //fix it. Display only.
            return false;
        }
        
        const actual = AccessSchema.safeParse(parsed_response.data.body);
        
        if (!actual.success) {
            console.error(`Login failed, can't process server response: ${parsed_response.data.body}`);
            return false;
        }
                
        const login: z.infer<typeof AccessSchema> = actual.data;

        context_data.static_access_token.current = login.access_token;
        context_data.setAccessToken(login.access_token);
        return true;
    }, []);

    const signup = useCallback(async (username: string, email: string, password: string, date_of_birth: string) => {
        const response = await Authrs.post("/signup", {
            username: username, email: email, password: password, date_of_birth: date_of_birth,
        }, {
            withCredentials: true,
        });

        const parsed_response = ResponseSchema.safeParse(response.data);
        
        if (!parsed_response.success) {
            console.error(`Signup failed, can't process server response: ${response.data}`);
            return false;
        }
        
        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, signup failed: ${error.error.issues}`);
                return false;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return false;
            }
        
            ErrorHandler(error.data.index, error.data.target, navigate); //fix it. Display only.
            return false;
        }
        
        const actual = AccessSchema.safeParse(parsed_response.data.body);
        
        if (!actual.success) {
            console.error(`Signup failed, can't process server response: ${parsed_response.data.body}`);
            return false;
        }
                
        const signup: z.infer<typeof AccessSchema> = actual.data;

        context_data.static_access_token.current = signup.access_token;
        context_data.setAccessToken(signup.access_token);
        return true;
    }, []);


    const refresh = async () => {
        return await __refresh();
    };


    return (
        <AuthHatch.Provider value={{
            refresh,
            login,
            signup,
        }}>
            { children }
        </AuthHatch.Provider>
    );
};