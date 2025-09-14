import React, { ReactNode, createContext, useContext } from "react";
import { CoreGlobalContext } from "./core";
import axios, { AxiosInstance } from "axios";
import { useNavigate } from "react-router-dom";
import { ErrorHandler } from "./handlers/error_handler";
import { z } from "zod";


const ErrorSchema = z.object({
    index: z.string(),
    target: z.string(),
});

const Oauth2Schema = z.object({
    access_token: z.string(),
    session_token: z.string(),
});

const RefreshSchema = z.object({
    session_token: z.string(),
});

const ResponseSchema = z.object({ //hbb - handled by backend
    status: z.boolean(),
    body: z.union([
        Oauth2Schema,
        RefreshSchema,
    ]),
    error: z.union([ErrorSchema.nullable()]),
});

interface AuthenticationProperties {
    children: ReactNode;
}

interface AuthProperties {
    refresh: () => void;
    login: (email: string, password: string) => void;
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

    if (!context_data.access_token) navigate(context_data.login_path.current);

    const Authrs: AxiosInstance = axios.create({
        baseURL: `${context_data.core_server_host.current}${context_data.api_oauth_addr.current}`,
        headers: {
            "access_token": `${context_data.access_token}`,
            "Content-Type": "application/json",
        },
    });


    const refresh = async () => { //leave async for now.
        const response = await Authrs.get("/refresh_session");

        const parsed_response = ResponseSchema.safeParse(response);
        
        if (!parsed_response.success) {
            console.error(`Refresh, can't process server response: ${parsed_response.data}`);
            navigate(context_data.login_path.current);
            return;
        }
        
        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, refresh failed: ${error.error.issues}`);
                navigate(context_data.login_path.current);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                navigate(context_data.login_path.current);
                return;
            }
        
            ErrorHandler(error.data.index, error.data.target, navigate); //fix it. Display only.
        }
        
        const actual = RefreshSchema.safeParse(parsed_response.data.body);
        
        if (!actual.success) {
            console.error(`Refresh failed, can't process server response: ${parsed_response.data.body}`);
            navigate(context_data.login_path.current);
            return;
        }
                
        const refresh: z.infer<typeof RefreshSchema> = actual.data;

        context_data.setSessionToken(refresh.session_token);
    };

    const login = async (email: string, password: string) => {
        const response = await Authrs.get("/login", {
            headers: { email: email, password: password },
        });

        const parsed_response = ResponseSchema.safeParse(response);
        
        if (!parsed_response.success) {
            console.error(`Login failed, can't process server response: ${parsed_response.data}`);
            return;
        }
        
        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, login failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }
        
            ErrorHandler(error.data.index, error.data.target, navigate); //fix it. Display only.
        }
        
        const actual = Oauth2Schema.safeParse(parsed_response.data.body);
        
        if (!actual.success) {
            console.error(`Login failed, can't process server response: ${parsed_response.data.body}`);
            return;
        }
                
        const login: z.infer<typeof Oauth2Schema> = actual.data;

        context_data.setAccessToken("access_token", login.access_token, { path: "/" });
        context_data.setSessionToken(login.session_token);
    };

    const signup = async (username: string, email: string, password: string, date_of_birth: string) => {
        const response = await Authrs.get("/signup", {
            headers: { username: username, email: email, password: password, date_of_birth: date_of_birth },
        });

        const parsed_response = ResponseSchema.safeParse(response);
        
        if (!parsed_response.success) {
            console.error(`Signup failed, can't process server response: ${parsed_response.data}`);
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
        }
        
        const actual = Oauth2Schema.safeParse(parsed_response.data.body);
        
        if (!actual.success) {
            console.error(`Signup failed, can't process server response: ${parsed_response.data.body}`);
            return false;
        }
                
        const signup: z.infer<typeof Oauth2Schema> = actual.data;

        context_data.setAccessToken("access_token", signup.access_token, { path: "/" });
        context_data.setSessionToken(signup.session_token);

        return true;
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