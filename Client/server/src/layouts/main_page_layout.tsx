import React from "react";

const MainPageLayout: React.FC = () => {
    return (
        <>
            <div id="header">
                <div id="label">
                    Name
                </div>
                <div className="header_option" id="about-us-option">
                    About Us
                </div>
                <div className="header_option" id="tos-option">
                    Our Terms of Service
                </div>
                <div className="header_option" id="privacy-policy-option">
                    Our Privacy Policy
                </div>
                <div id="action-panel">
                    <div id="open-in-browser">
                        Open in browser
                    </div>
                    <div id="download-app">
                        Download our app
                    </div>
                </div>
            </div>
            <div id="main">
                <div id="main-label">
                    <div className="main_label_letter">N</div>
                    <div className="main_label_letter">A</div>
                    <div className="main_label_letter">M</div>
                    <div className="main_label_letter">E</div>
                </div>
                <div id="about-us">
                    <div id="about-us-header">About Us</div>
                    <div id="about-us-content">
                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed volutpat dolor augue, cursus egestas urna feugiat at. 
                        Phasellus gravida, ligula eget feugiat gravida, lectus elit lobortis dui, gravida consectetur risus ligula nec s
                        apien. Proin ac vestibulum felis. Nullam dolor massa, fringilla eu condimentum vestibulum, fermentum id quam. Nullam
                        non porttitor augue. Cras tempus urna quis orci maximus, vitae cursus tortor mollis. Aliquam at erat nibh. Aliquam
                        erat volutpat. Sed dignissim tellus sit amet convallis egestas. Nunc dapibus ultricies neque, ac rutrum mauris gra
                        vida vel. Vestibulum interdum lacus vel ipsum fringilla rutrum. Sed vitae massa elit. Aenean interdum eros ac mi dign
                        issim pretium. Aenean vulputate felis metus, eget maximus tellus mattis non.
                        <br></br><br></br>
                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed volutpat dolor augue, cursus egestas urna feugiat at. 
                        Phasellus gravida, ligula eget feugiat gravida, lectus elit lobortis dui, gravida consectetur risus ligula nec s
                        apien. Proin ac vestibulum felis. Nullam dolor massa, fringilla eu condimentum vestibulum, fermentum id quam. Nullam
                        non porttitor augue. Cras tempus urna quis orci maximus, vitae cursus tortor mollis. Aliquam at erat nibh. Aliquam
                        erat volutpat. Sed dignissim tellus sit amet convallis egestas. Nunc dapibus ultricies neque, ac rutrum mauris gra
                        vida vel. Vestibulum interdum lacus vel ipsum fringilla rutrum. Sed vitae massa elit. Aenean interdum eros ac mi dign
                        issim pretium. Aenean vulputate felis metus, eget maximus tellus mattis non.
                        <br></br><br></br>
                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed volutpat dolor augue, cursus egestas urna feugiat at. 
                        Phasellus gravida, ligula eget feugiat gravida, lectus elit lobortis dui, gravida consectetur risus ligula nec s
                        apien. Proin ac vestibulum felis. Nullam dolor massa, fringilla eu condimentum vestibulum, fermentum id quam. Nullam
                        non porttitor augue. Cras tempus urna quis orci maximus, vitae cursus tortor mollis. Aliquam at erat nibh. Aliquam
                        erat volutpat. Sed dignissim tellus sit amet convallis egestas. Nunc dapibus ultricies neque, ac rutrum mauris gra
                        vida vel. Vestibulum interdum lacus vel ipsum fringilla rutrum. Sed vitae massa elit. Aenean interdum eros ac mi dign
                        issim pretium. Aenean vulputate felis metus, eget maximus tellus mattis non.
                    </div>
                </div>
            </div>
            <div id="footer">

            </div>
        </>
    );
};

export default MainPageLayout;