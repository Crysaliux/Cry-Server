import React, { ReactHTMLElement, useContext, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { CoreGlobalContext } from "services/core";
import styles from "../static/main_page.module.css";


const MainPageLayout: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const navigate = useNavigate();

    return (
        <div id={styles.mainPageContainer}>
            <div id={styles.header}>
                <div id={styles.label}>
                    Name
                </div>
                <div className={styles.headerOption} id={styles.aboutUsOption}>
                    About Us
                </div>
                <div className={styles.headerOption} id={styles.tosOption}>
                    Our Terms of Service
                </div>
                <div className={styles.headerOption} id={styles.privacyPolicyOption}>
                    Our Privacy Policy
                </div>
                <div id={styles.actionPanel}>
                    <div id={styles.openInBrowser} onClick={() => navigate(context_data.login_path.current)}>
                        Open in browser
                    </div>
                    <div id={styles.downloadApp} onClick={() => navigate("/unknown")}>
                        Download our app
                    </div>
                </div>
            </div>
            <div id={styles.main}>
                <div id={styles.mainLabel}>
                    <div className={styles.mainLabelLetter}>N</div>
                    <div className={styles.mainLabelLetter}>A</div>
                    <div className={styles.mainLabelLetter}>M</div>
                    <div className={styles.mainLabelLetter}>E</div>
                </div>
                <div id={styles.aboutUs}>
                    <div id={styles.aboutUsHeader}>About Us</div>
                    <div id={styles.aboutUsContent}>
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
        </div>
    );
};

export default MainPageLayout;