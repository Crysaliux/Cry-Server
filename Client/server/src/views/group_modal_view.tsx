import React, { useState, Dispatch, FormEvent, SetStateAction, useRef, useEffect } from "react";
import { Group } from "../components/groups";
import '../static/client_interface.css';

interface GroupModalViewProperties {
    group_modal_status: boolean;
    set_group_modal_status: Dispatch<SetStateAction<boolean>>;
    set_group_to_create: Dispatch<SetStateAction<Group | null>>;
    set_error: Dispatch<SetStateAction<string | null>>;
}

interface APIResponse {
    url: string | null;
}

const GroupModalView: React.FC<GroupModalViewProperties> = ({ group_modal_status, set_group_modal_status, set_group_to_create, set_error }) => {
    const [selected_icon_path, SetSelectedIconPath] = useState<string>('');
    const GroupModalIconReference = useRef<HTMLDivElement>(null);
    const GroupModalNameReference = useRef<HTMLTextAreaElement>(null);
    const GroupModalDescReference = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (selected_icon_path !== '' && GroupModalIconReference.current) {
            GroupModalIconReference.current.style.backgroundImage = `url(${selected_icon_path})`;
        }
    }, [selected_icon_path]);

    const OnChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const icon = event.target.files?.[0];
        if (icon && icon.type.startsWith('image/')) {
            try {
                 const formData = new FormData();
                 formData.append('icon', icon as File);

                 const response = await fetch('https://somehost/client/save_image', {
                    method: 'POST',
                    body: formData
                 });

                 const data: APIResponse = await response.json();

                 if (data.url !== null) {
                    const full_path = `https://somehost/client/${data.url}`;
                    SetSelectedIconPath(full_path);
                 } else {
                    set_error('Application error. No data has been received.');
                 }
            } catch (error) {
                set_error("Application error. Can't connect to the API server.");
            }
        }
    };

    const CreateGroup = () => {
        if (GroupModalNameReference.current && GroupModalDescReference.current) {
            if (selected_icon_path === '') {
                SetSelectedIconPath('https://somehost/client/basic_group_image.png');
            }

            const NewGroup: Group = {
                type: 'group',
                id: crypto.randomUUID(),
                owner_id: 55555, //To be implemented!
                icon_path: selected_icon_path,
                name: GroupModalNameReference.current.value,
                desc: GroupModalDescReference.current.value
            };
            set_group_to_create(NewGroup);
        } else {
            set_error("Ooops! Group name and description can't be left blank!");
        }
    };

    if (group_modal_status) {
        return (
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
                        <button className="button underlined small nocopy" onClick={() => set_group_modal_status(false)}>Cancel</button>
                    </div>
                </div>

                <div id="modal-blur-overlay"></div>
            </>
        );
    } else {
        return null;
    }
};

export default GroupModalView;