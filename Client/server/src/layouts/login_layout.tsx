import React from "react";

const LoginLayout: React.FC = () => {
    return (
        <>
            <div id="sign-up-form">
                <div className="section_header">Welcome back!</div>
                <input type="email" placeholder="Your email" className="field" maxLength={35} id="email"></input>
                <div id="password-section">
                    <input type="password" placeholder="Your password" maxLength={35} id="password"></input>
                    <div id="show-password"></div>
                </div>
                <div id="login">Log in</div>
                <div id="forgot-password">Forgot your password?</div>
            </div>
        </>
    );
};

export default LoginLayout;