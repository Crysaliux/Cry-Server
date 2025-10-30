import React, { useEffect } from "react";
import { createPortal } from "react-dom";
import { useContext } from "react";
import { CoreGlobalContext } from "services/core";
import { APIHatch } from "services/api_listener";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { Outlet } from "react-router-dom";
import { validate, version } from 'uuid';
import LoadingLayout from "layouts/loading_layout";
import TextareaAutosize from "react-textarea-autosize";
import styles from "../static/group.module.css";
import { 
    useGroups,  
    useRooms, 
    useSpaces,
} from "services/worker";
import { CSSProperties } from "@mui/material";


const GroupLayout: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const api_hatch = useContext(APIHatch);
    if (!api_hatch) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const groups = useGroups();
    const rooms = useRooms();
    const spaces = useSpaces();

    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        if (!context_data.gateway_ready.status) return;

        const [_, group_global_name, room_id] = location.pathname.split("/");

        if (context_data.group_ignore.current.includes("/" + group_global_name)
            || context_data.group_ignore.current.includes("/" + room_id)) return;

        if (group_global_name) {
            if (room_id === undefined) {
                api_hatch.getPrimaryRoom(group_global_name).then(data => {
                    if (data.exists) {
                        if (data.room_id) {
                            navigate(`/${group_global_name}/${room_id}`);
                        } else {
                            navigate(location.pathname + context_data.room_void_path.current);
                        }
                    }
                });
            } else {
                if (room_id === context_data.room_void_path.current) { //we don't count void!
                    return;
                }

                if (context_data.current_group.current) {
                    if (context_data.current_group.current.global_name !== group_global_name) {
                        api_hatch.fetchGroup(group_global_name, room_id);
                        //setting current group, preferrably in fetchGroup()
                    } else {
                        api_hatch.fetchMessages(group_global_name, room_id);
                        //setting current room, preferrably in fetchMessages()
                    }
                } else api_hatch.fetchGroup(group_global_name, room_id);
                //setting current group, preferrably in fetchGroup()
            }

        } else return;
    }, [location, context_data.gateway_ready.status]); 

    const groups_array = Object.values(groups);
    const rooms_array = Object.values(rooms);
    const spaces_array = Object.values(spaces);

    const orphan_rooms = rooms_array.filter((room) => room.space_id === null);
    const FetchChildRooms = (space_id: string) => {
        return rooms_array.filter((room) => room.space_id === space_id);
    };

    if (!context_data.gateway_ready.status) return (
        <LoadingLayout />
    );

    return (
        <div id={styles.groupContainer}>
            <div id={styles.header}>
                <div id={styles.headerBuffer}></div>
                <div id={styles.channelName}>
                    Channel name
                </div>
                <div id={styles.manageMembers}>
                    <div id={styles.invite}>

                    </div>
                    <div id={styles.sortBy}>
                        <div id={styles.sortByArrow}></div>
                        Roles
                    </div>
                    <div id={styles.hideMembers}>

                    </div>
                </div>
            </div>
                    
            <div id={styles.groups}>
                <div id={styles.toContacts} onClick={() => navigate(context_data.contacts_path.current)}>
                    <div id={styles.toContactsShrunk}></div>
                </div>
                <hr className={styles.divisionLine}></hr>
                        
                {groups_array.map(group => (
                    <div className={styles.group} key={group.id} style={{ "--group-background": `url(${group.icon_url})` } as CSSProperties} onClick={() => navigate(context_data.main_path.current + group.global_name)}>
                        <div className={styles.groupShrunk}></div>
                    </div>
                ))}

                <hr className={styles.divisionLine}></hr>
                <div id={styles.createGroup} onClick={() => navigate(location.pathname + context_data.group_creation_modal_path.current)}>
                    <div id={styles.createGroupShrunk}></div>
                </div>
            </div>

            <div id={styles.rooms}>
                <div id={styles.actions}>
                    <div id={styles.groupHeader}>
                        Group name
                        <div id={styles.settings}></div>
                    </div>
                    <div className={styles.action}>Add room</div>
                    <div className={styles.action}>Add space</div>
                </div>
                <hr className={styles.divisionLine}></hr>
                {orphan_rooms.map(room => (
                    <div className={styles.room} key={room.id}>
                        <div className={styles.hashtag}>#</div>{ room.name }
                    </div>
                ))}
                {spaces_array.map(space => (
                    <div className={styles.space} key={space.id}>
                        <div className={styles.spaceName}>{ space.name }</div>
                        {FetchChildRooms(space.id).map(room => (
                            <div className={styles.room} key={room.id}>
                                <div className={styles.hashtag}>#</div>{ room.name }
                            </div>
                        ))}
                    </div>
                ))}
            </div>
            <Outlet />
        </div>
    );
};

export default React.memo(GroupLayout);