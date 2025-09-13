import React from "react";

//<div id="signup-instead">Signup instead</div>
const LoginLayout: React.FC = () => {
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
                <div id="forgot-password">Forgot your password?</div>
            </div>
        </div>
    );
};

export default LoginLayout;