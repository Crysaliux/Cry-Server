import React from "react";


const SignUpLayout: React.FC = () => {
    return (
        <>
            <div id="sign-up-form">
                <div className="section_header">general</div>
                <input type="text" placeholder="Your username" className="field" maxLength={35} id="username"></input>
                <div className="help">
                    - lowercase characters only!
                </div>
                <div className="section_header">safety</div>
                <input type="email" placeholder="Your email" className="field" maxLength={35} id="email"></input>
                <div id="password-section">
                    <input type="password" placeholder="Your password" maxLength={35} id="password"></input>
                    <div id="show-password"></div>
                </div>
                <div className="help">
                    - make sure it's a strong one <br></br>
                    - don't share it with anyone, even us!
                </div>
                <div className="section_header">Almost there!</div>
                <div id="create-account">Create acount!</div>
            </div>
        </>
    );
};

export default SignUpLayout;