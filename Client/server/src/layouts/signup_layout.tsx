import React, { useContext, useEffect, useRef, useState } from "react";
import { CoreGlobalContext } from "services/core";
import { useNavigate } from "react-router-dom";


const SignUpLayout: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const navigate = useNavigate();

    const password_field_ref = useRef<HTMLInputElement>(null);
    const show_password_ref = useRef<HTMLDivElement>(null);
    const password_saved = useRef<string>("");

    const [password_field_type, setPasswordFieldType] = useState<string>("password");

    const showPassword = () => {
        if (password_field_ref.current && show_password_ref.current) {
            password_saved.current = password_field_ref.current.value;
            if (password_field_ref.current.type === "password") {
                setPasswordFieldType("text");
                show_password_ref.current.style.backgroundImage = "../assets/oauth/eye_opened.svg"
                password_field_ref.current.value = password_saved.current;
            } else {
                setPasswordFieldType("password");
                show_password_ref.current.style.backgroundImage = "../assets/oauth/eye_closed.svg"
                password_field_ref.current.value = password_saved.current;
            }
        }
    };

    return (
        <div id="signup-container">
            <div id="sign-up-form">
                <div className="section_header">general</div>
                <input type="text" placeholder="Your username" className="field" maxLength={35} id="username"></input>
                <div className="help">
                    - lowercase characters only!
                </div>
                <div className="section_header">safety</div>
                <input type="email" placeholder="Your email" className="field" maxLength={35} id="email"></input>
                <div id="password-section">
                    <input type={password_field_type} placeholder="Your password" maxLength={35} id="password" ref={password_field_ref}></input>
                    <div id="show-password" onClick={() => showPassword()} ref={show_password_ref}></div>
                </div>
                <div className="help">
                    - make sure it's a strong one <br></br>
                    - don't share it with anyone, even us!
                </div>
                <div className="section_header">Almost there!</div>
                <div id="create-account">Create account!</div>
                <div id="login-instead" onClick={() => navigate(context_data.login_path.current)}>I already have an account!</div>
            </div>
        </div>
    );
};

export default SignUpLayout;