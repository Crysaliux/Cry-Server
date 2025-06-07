import React, { useState, Dispatch, FormEvent, SetStateAction, useRef, useEffect, useContext } from "react";
import { customAlphabet } from "nanoid";
import { GlobalContext } from 'services/global_manager';
import { ListenerHatch } from "services/listener";
import { Modal } from "components/overlay/modal";
import { Field } from "components/overlay/field";

interface APIResponse {
    success: boolean;
    url: string | null;
}

const ModalView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    const listener_hatch = useContext(ListenerHatch);
    if (!context_data || !listener_hatch) {
        throw new Error("Context for modal_view can't be defined.");
    }
    const [modal_image_select_path, SetModalImageSelectPath] = useState<string>('');
    const index = useRef<string>(crypto.randomUUID());

    const ModalReference = useRef<Modal| null>(null);
    if (context_data.current_modal.current) {
        ModalReference.current = context_data.current_modal.current;
    }
    const SubmitButtonReference = useRef<HTMLButtonElement>(null);
    const ModalImageReference = useRef<HTMLInputElement>(null);
    const long_field_default_height = useRef<number | null>(null);
    const long_field_first_growth_height = useRef<number | null>(null);
    const version = useRef(0);
    const display_fields = useRef<Field[] | null>(null);
    const id_gen = customAlphabet('123456789', 16);

    if (ModalReference.current) {
        display_fields.current = ModalReference.current.fields.filter(field => field.display === true);
        if (ModalImageReference.current) {
            ModalImageReference.current.style.backgroundImage = `url(${modal_image_select_path})`;
        }
    }

    //...group, ...data as Partial<Group>

    const OnFieldChange = async (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        if (ModalReference.current) {
            if (long_field_default_height.current) {
                if (!long_field_first_growth_height.current && event.target.scrollHeight > long_field_default_height.current) {
                    long_field_first_growth_height.current = event.target.scrollHeight;
                }
            } else {
                long_field_default_height.current = event.target.scrollHeight;
            }

            if (event.target.dataset.input_length === 'long') {
                if (long_field_first_growth_height.current) {
                    if (event.target.scrollHeight > long_field_first_growth_height.current) {
                        event.target.style.height = 'auto';
                        event.target.style.height = `${event.target.scrollHeight}px`;
                    } else {
                       event.target.style.height = `${event.target.scrollHeight}px`;
                    }
                } else { 
                    event.target.style.height = `${long_field_default_height.current}px`;
                }
                console.log(long_field_first_growth_height.current);
            }
            ModalReference.current.fields = ModalReference.current.fields.map(
                field => field.index === event.target.dataset.index ? { ...field, input: event.target.value } : field);
            if (context_data.current_modal_failed_attempt.current === true) {
                context_data.current_modal_failed_attempt.current = false;
            }
            if (SubmitButtonReference.current) {
                if (ModalReference.current.fields.every(field => field.input !== '')) {
                    SubmitButtonReference.current.className = `button ${ModalReference.current.submit_colour} small nocopy`;
                } else {
                    SubmitButtonReference.current.className = `button ${ModalReference.current.submit_colour}_clicked small nocopy`;
                }
            }
        }
    };

    const OnSelectImagechange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        if (ModalReference.current) {
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
                        version.current += 1;
                        SetModalImageSelectPath(`${data.url}?v=${version.current}`);
                        ModalReference.current.image_select_path = data.url;
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
        if (ModalReference.current) {
            if (ModalReference.current.fields.every(field => field.input !== '') && !context_data.current_modal_failed_attempt.current) {
                if (SubmitButtonReference.current) {
                    SubmitButtonReference.current.className = `button ${ModalReference.current.submit_colour}_clicked small nocopy`;
                }
                ModalReference.current.id = Number(id_gen());
                listener_hatch.SendRequest(ModalReference.current);
            }
        }
    }

    const EvaluateInputlength = (length: string) => {
        switch(length) {
            case 'long':
                return 300;
            case 'short':
                return 30;
        }
    };

    if (ModalReference.current && context_data.modal_display_status && display_fields.current) {
        return (
            <>  
                <div className="modal border" id={ModalReference.current.index}>
                    {
                        ModalReference.current.image_select ?
                        <div ref={ModalImageReference} className="modal_image">
                            <input className="modal_image_input" type="file" accept="image/png, image/jpeg" onChange={OnSelectImagechange}></input>
                        </div>
                        : null
                    }
                    {display_fields.current.map(field => (
                        <div className="modal_input" key={field.index}>
                            <div className="input_info medium nocopy">{field.header}</div>
                            <textarea maxLength={EvaluateInputlength(field.input_length)} className='modal_input_field no_border' onChange={OnFieldChange} data-input_length={field.input_length} data-index={field.index}></textarea>
                        </div>
                    ))}
                    <div className="modal_choice">
                        <button ref={SubmitButtonReference} className={`button ${ModalReference.current.submit_colour}_clicked small nocopy`} onClick={SubmitModal}>{ModalReference.current.submit_text}</button>
                        <button className="button underlined small nocopy" onClick={() => context_data.SetModalDisplayStatus(false)}>Cancel</button>
                    </div>
                </div>

                <div id="modal-blur-overlay"></div>
            </>
        );
    } else {
        return null;
    }
};

export default ModalView;