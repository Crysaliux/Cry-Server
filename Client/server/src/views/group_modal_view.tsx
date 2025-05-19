import React, { useState, Dispatch, FormEvent, SetStateAction, useRef, useEffect, useContext } from "react";
import { GlobalContext } from '../services/context_manager';
import { Group } from "../components/groups";
import '../static/client_interface.css';

interface APIResponse {
    success: boolean;
    url: string | null;
}

const GroupModalView: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for groups_view can't be defined.");
    }
    const [current_icon_path, SetCurrentIconPath] = useState<string>('');
    const GroupModalIconReference = useRef<HTMLDivElement>(null);
    const GroupModalNameReference = useRef<HTMLTextAreaElement>(null);
    const GroupModalDescReference = useRef<HTMLTextAreaElement>(null);
    const session_id = crypto.randomUUID();

    useEffect(() => {
        if (GroupModalIconReference.current) {
            GroupModalIconReference.current.style.backgroundImage = `url(${current_icon_path})`;
        }
    }, [current_icon_path])

    const OnChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const icon = event.target.files?.[0];
        if (icon && icon.type.startsWith('image/')) {
            try {
                const formData = new FormData();
                formData.append('file', icon as File);
                formData.append('index', crypto.randomUUID());
                formData.append('session_id', session_id);
                const response = await fetch('http://localhost:8080/client/upload_group_icon', {
                    method: 'POST',
                    body: formData
                });
                const data: APIResponse = await response.json();
                if (data.url !== null) {
                    SetCurrentIconPath(data.url);
                } else {
                    context_data.SetError('Application error. No data has been received.');
                }
            } catch (error) {
                context_data.SetError("Application error. Can't connect to the API server.");
            }
        }
    };

    const Selected = async () => {
        try {
            const formData = new FormData();
            formData.append('session_id', session_id);
            formData.append('set_path', current_icon_path);
            const response = await fetch('http://localhost/client/group_icon_set', {
                method: 'POST',
                body: formData
            });
            const data: Partial<APIResponse> = await response.json();
            if (data.success) {
                return true;
            } else {
                context_data.SetError('Application error. No data has been received.');
                return false;
            }
        } catch(error) {
            context_data.SetError("Application error. Can't connect to the API server.");
            return false;
        }
    };

    const CreateGroup = async () => {
        if (GroupModalNameReference.current && GroupModalDescReference.current) {
            if (current_icon_path === '') {
                SetCurrentIconPath('');
            } else {
                const status = await Selected();
                if (!status) {
                    SetCurrentIconPath('');
                }
            }
            const NewGroup: Group = {
                type: 'group',
                id: parseInt(crypto.randomUUID().replace(/\D/g, ''), 10),
                owner_id: 5555, //To be implemented!
                icon_path: current_icon_path,
                name: GroupModalNameReference.current.value,
                desc: GroupModalDescReference.current.value
            };
            context_data.SetGroupToCreate(NewGroup);
        } else {
            context_data.SetError("Ooops! Group name and description can't be left blank!");
        }
    };

    return (
        <>
            {
                context_data.group_modal_status ? 
                <>
                    <div className="modal" id="group-modal">
                        <div id="group-modal-icon" ref={GroupModalIconReference}>
                            <input id="group-modal-icon-input" type="file" accept="image/png, image/jpeg" onChange={OnChange}></input>
                        </div>
                        <div className="modal_input" id="group-modal-name">
                            <div className="input_info medium nocopy">What should we call your group?</div>
                            <textarea maxLength={30} className="modal_input_field short_input" ref={GroupModalNameReference}></textarea>
                        </div>
                        <div className="modal_input" id="group-modal-description">
                            <div className="input_info medium nocopy">What will this group be for?</div>
                            <textarea maxLength={300} className="modal_input_field long_input" ref={GroupModalDescReference}></textarea>
                        </div>
                        <div className="modal_choice" id="group-modal-choice">
                            <button className="button blue small nocopy" onClick={CreateGroup}>Create Group</button>
                            <button className="button underlined small nocopy" onClick={() => context_data.SetGroupModalStatus(false)}>Cancel</button>
                        </div>
                    </div>

                    <div id="modal-blur-overlay"></div>
                </> : null
            }
        </>
    );
};

export default GroupModalView;