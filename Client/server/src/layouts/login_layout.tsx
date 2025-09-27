import React, { useContext, useRef, useState, useEffect } from "react";
import { CoreGlobalContext } from "services/core";
import { useNavigate } from "react-router-dom";
import { AuthHatch } from "services/oauth";


interface InputConfig {
    type: string;
    background_svg: string;
}

const LoginLayout: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const auth_hatch = useContext(AuthHatch);
    if (!auth_hatch) {
        throw new Error("Can't load AuthHatch for oauth");
    }

    const navigate = useNavigate();

    const email_field_ref = useRef<HTMLInputElement>(null);
    const password_field_ref = useRef<HTMLInputElement>(null);

    const [input_config, setInputConfig] = useState<InputConfig>({"type": "password", 
            "background_svg": "../public/oauth/eye_closed.svg"});

    useEffect(() => {
        if (context_data.access_token) navigate(context_data.client_path.current);
    }, [navigate, context_data.access_token]);
    
    const showPassword = () => {
        if (password_field_ref.current) {
            if (password_field_ref.current.type === "password") {
                setInputConfig({"type": "text", 
                    "background_svg": "../public/oauth/eye_opened.svg"});
            } else {
                setInputConfig({"type": "password",
                    "background_svg": "../public/oauth/eye_closed.svg"});
            }
        }
    };

    const submitData = async () => {
        if (email_field_ref.current && password_field_ref.current) {
            if (email_field_ref.current.value === "") {
                //
                console.warn("Email field can't be empty!");
                return;
            }

            if (password_field_ref.current.value === "") {
                //
                console.warn("Password field can't be empty!");
                return;
            }

            const status = await auth_hatch.login(
                email_field_ref.current.value,
                password_field_ref.current.value,
            );
            
            if (status) {
                navigate(context_data.client_path.current);
            };
        }
    };

    if (context_data.access_token) return null;

    return (
        <div id="login-container">
            <div id="login-form">
                <div className="section_header">Welcome back!</div>
                <input type="email" placeholder="Your email" className="field" maxLength={35} id="email" ref={email_field_ref}></input>
                <div id="password-section">
                    <input type={input_config.type} placeholder="Your password" maxLength={35} id="password" ref={password_field_ref}></input>
                    <div id="login-show-password" onClick={() => showPassword()} style={{backgroundImage: `url(${input_config.background_svg})`}}></div>
                </div>
                <div id="login" onClick={() => submitData()}>Log in</div>
                <div id="signup-instead" onClick={() => navigate(context_data.signup_path.current)}>Signup instead</div>
                <div id="forgot-password">Forgot your password?</div>
            </div>
        </div>
    );
};

export default LoginLayout;