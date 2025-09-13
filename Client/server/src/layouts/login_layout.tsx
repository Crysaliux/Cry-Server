import React, { useContext } from "react";
import { CoreGlobalContext } from "services/core";
import { useNavigate } from "react-router-dom";

//<div id="signup-instead">Signup instead</div>
const LoginLayout: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const navigate = useNavigate();

    return (
        <div id="login-container">
            <div id="login-form">
                <div className="section_header">Welcome back!</div>
                <input type="email" placeholder="Your email" className="field" maxLength={35} id="email"></input>
                <div id="password-section">
                    <input type="password" placeholder="Your password" maxLength={35} id="password"></input>
                    <div id="show-password"></div>
                </div>
                <div id="login">Log in</div>
                <div id="signup-instead" onClick={() => navigate(context_data.signup_path.current)}>Signup instead</div>
                <div id="forgot-password">Forgot your password?</div>
            </div>
        </div>
    );
};

export default LoginLayout;