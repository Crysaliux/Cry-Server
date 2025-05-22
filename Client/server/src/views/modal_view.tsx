import React, { useState, Dispatch, FormEvent, SetStateAction, useRef, useEffect, useContext } from "react";
import { GlobalContext } from '../services/global_manager';
import { Modal } from "../components/overlay/modal";
import '../static/client_interface.css';
import { Listener } from "services/listener";

interface APIResponse {
    success: boolean;
    url: string | null;
}

const ModalView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
    }
    const [modal_image_select_path, SetModalImageSelectPath] = useState<string>('');
    let modal_reference = useRef(context_data.display_modal as Modal);
    let native_submit_colour = useRef('');
    const index = useRef(crypto.randomUUID());
    const submit_button_class = useRef('button blue small nocopy');

    const ModalSubmitReference = useRef<HTMLButtonElement>(null);
    const ModalImageReference = useRef<HTMLInputElement>(null);

    if (ModalSubmitReference.current) {
        native_submit_colour.current = window.getComputedStyle(ModalSubmitReference.current).backgroundColor;
    }

    if (ModalImageReference.current) {
        ModalImageReference.current.style.backgroundImage = `url(${modal_image_select_path})`;
    }

    if (context_data.display_modal) {
        submit_button_class.current = `button ${context_data.display_modal.submit_colour} small nocopy`;
    }

    //...group, ...data as Partial<Group>

    const OnFieldChange = async (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        if (modal_reference.current) {
            modal_reference.current.fields = modal_reference.current.fields.map(
                field => field.index === event.target.dataset.index ? { ...field, data: { input: event.target.value } } : field);
        }
    };

    const OnSelectImagechange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        if (modal_reference.current) {
            const image = event.target.files?.[0];
            if (image && image.type.startsWith('image/')) {
                try {
                    const formData = new FormData();
                    formData.append('file', image as File);
                    formData.append('index', index.current);
                    const response = await fetch('http://localhost:8080/client/upload_dynamic', {
                        method: 'POST',
                        body: formData
                    });
                    const data: APIResponse = await response.json();
                    if (data.url !== null) {
                        SetModalImageSelectPath(data.url);
                        modal_reference.current.image_select_path = data.url;
                    } else {
                        context_data.SetError('Looks like our servers arent responding properly, maybe try again later');
                    }
                } catch(error) {
                    context_data.SetError("Odd, seems you cant connect to our servers, check if your internet is working or try again later");
                }
            }
        }
    };

    const SubmitModal = async () => {
        if (modal_reference.current) {
            if (modal_reference.current.fields.every(field => field.input !== '')) {
                if (ModalSubmitReference.current) {
                    ModalSubmitReference.current.style.backgroundColor = `${native_submit_colour.current.replace(')', ', 0.5)')}`;
                }
                context_data.SetModalSubmitRequest(modal_reference.current);
            } else {
                context_data.SetError('Hmmm you cant leave some fields blank like that');
            }
        }
    }

    const Evaluate = (length: string) => {
        switch(length) {
            case 'long':
                return 300;
            case 'short':
                return 30;
        }
    };

    return (
        <>
            {
                context_data.display_modal ? 
                <>
                    <div className="modal border" id={context_data.display_modal.index}>
                        {
                            context_data.display_modal.image_select ?
                            <div ref={ModalImageReference} className="modal_image">
                                <input className="modal_image_input" type="file" accept="image/png, image/jpeg" onChange={OnSelectImagechange}></input>
                            </div>
                            : null
                        }
                        {context_data.display_modal.fields.map(field => (
                            <div className="modal_input" key={field.index}>
                                <div className="input_info medium nocopy">{field.header}</div>
                                <textarea maxLength={Evaluate(field.input_length)} className="modal_input_field {field.input_length}" onChange={OnFieldChange}></textarea>
                            </div>
                        ))}
                        <div className="modal_choice">
                            <button className={submit_button_class.current} ref={ModalSubmitReference} onClick={SubmitModal}>Create</button>
                            <button className="button underlined small nocopy" onClick={() => context_data.SetDisplayModal(null)}>Cancel</button>
                        </div>
                    </div>

                    <div id="modal-blur-overlay"></div>
                </> : null
            }
        </>
    );
};

export default ModalView;