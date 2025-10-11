import React, { ChangeEvent, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useContext } from "react";
import { CoreGlobalContext } from "services/core";
import { useLocation, useNavigate } from "react-router-dom";
import TextareaAutosize from "react-textarea-autosize";
import { useCompress } from "services/handlers/image_handlers";
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
    const [cropped_area_pixels, setCroppedAreaPixels] = useState<any>(null);
    
    const canvas_ref = useRef<HTMLCanvasElement>(null);

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

            const compressed = await useCompress(event.target.files[0]);
            reader.readAsDataURL(compressed);
        }
    };

    const handleCropComplete = (croppedArea: any, croppedAreaPixels: any) => {
        setCroppedAreaPixels(croppedAreaPixels);
    };

    const useCrop = async (shape: string = "default") => { //Make it a handler!
        const canvas = canvas_ref.current;
        if (!canvas) {
            return; //maybe return an error?
        }

        const ctx = canvas.getContext("2d");

        if (!ctx) {
            return; //maybe return an error?
        }

        const reader = new FileReader();
        reader.onloadend = () => {
            setImageData(reader.result);
            setImageSelected(false);
        };

        canvas.width = cropped_area_pixels.width;
        canvas.height = cropped_area_pixels.height;

        const img = new Image();
        img.src = String(image_data);
        img.onload = () => {

            if (shape === "circle") {
                ctx.beginPath();
                ctx.arc(
                    cropped_area_pixels.width / 2,
                    cropped_area_pixels.height / 2,
                    cropped_area_pixels.width / 2,
                    0,
                    2 * Math.PI
                );
                ctx.closePath();
                ctx.clip();
            }

            ctx.drawImage(
                img,
                cropped_area_pixels.x,
                cropped_area_pixels.y,
                cropped_area_pixels.width,
                cropped_area_pixels.height,
                0,
                0,
                cropped_area_pixels.width,
                cropped_area_pixels.height
            );

            canvas.toBlob(
                (blob) => {
                    if (blob) reader.readAsDataURL(blob);
                },
                "image/jpeg",
                0.9
            );
        };
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
        <div id={styles.modalContainer}>
            <div id={styles.cropContainer}>
                <div id={styles.cropImgContainer}>
                    <Cropper
                        cropSize={{ width: 500, height: 500 }}
                        image={String(image_data)}
                        crop={crop}
                        zoom={zoom}
                        aspect={1}
                        cropShape="rect"
                        showGrid={false}
                        objectFit="contain"
                        onCropComplete={handleCropComplete}
                        onCropChange={(crop) => setCrop(crop)}
                        onZoomChange={(zoom) => setZoom(zoom)}
                    />
                    <canvas style={{ display: "none" }} ref={canvas_ref}></canvas>
                </div>
                <div id={styles.cropperCropAndSave} onClick={() => useCrop()}>Crop and save</div>
            </div>
        </div>,
        modal_root
    );
};