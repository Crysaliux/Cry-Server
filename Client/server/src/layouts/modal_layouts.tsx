import React, { ChangeEvent, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useContext } from "react";
import { CoreGlobalContext } from "services/core";
import { useLocation, useNavigate } from "react-router-dom";
import TextareaAutosize from "react-textarea-autosize";
import Cropper from 'react-easy-crop'
import styles from "../static/modals.module.css";


export const CreateGroupModal: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const modal_root = document.getElementById("modal-root");
    if (!modal_root) {
        throw new Error("Can't load modal-root for CreateGroupModal");
    }

    const location = useLocation();
    const navigate = useNavigate();

    const [image_selected, setImageSelected] = useState<boolean>(false);
    const [image_data, setImageData] = useState<string | null | ArrayBuffer>("");

    const [crop, setCrop] = useState({ x: 0, y: 0 });
    const [zoom, setZoom] = useState(1);
    const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);

    const cancelCreation = () => {
        navigate(location.pathname.replace(context_data.group_creation_modal_path.current, ""));
    };

    const onImageSelected = async (event: ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files.length > 0) {
            const reader = new FileReader();
            reader.onloadend = () => {
                setImageData(reader.result);
                setImageSelected(true);
            };
            reader.readAsDataURL(event.target.files[0]);
        }
    };
    
    if (!image_selected) {
        return createPortal(
            <div id={styles.modalContainer}>
                <div id={styles.groupModalForm}>
                    <div id={styles.cancel}>
                        <div id={styles.cancelCross} onClick={() => cancelCreation()}></div>
                    </div>
                    <div id={styles.modalGroupImg} style={{ backgroundImage: image_data? `url(${String(image_data)})` : "none" }}>
                        <input  type="file" accept="image/*" id={styles.modalGroupImgInput} onChange={onImageSelected}></input>
                    </div>
                    <div className={styles.sectionHeader}>Creating new group</div>
                    <input type="text" placeholder="Group name" className={styles.field} maxLength={25}></input>
                    <div className={styles.sectionHeader}>Anything fun?</div>
                    <div id={styles.aboutGroupArea}>
                        <TextareaAutosize id={styles.aboutGroupField} maxLength={250} placeholder="About group..."></TextareaAutosize>
                    </div>
                    <div id={styles.modalCreateGroup}>Create Group</div>
                </div>
            </div>,
            modal_root
        );
    }

    return createPortal(
        <div className={styles.cropContainer}>
            <Cropper
                image={String(image_data)}
                crop={crop}
                zoom={zoom}
                aspect={1}
                cropShape="round"
                showGrid={false}
                onCropChange={(crop) => setCrop(crop)}
                onCropComplete={() => setImageSelected(false)}
                onZoomChange={(zoom) => setZoom(zoom)}
            />
        </div>,
        modal_root //finish this and move on!
    );
};