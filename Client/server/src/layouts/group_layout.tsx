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
    const { group_id, room_id } = useParams();

    useEffect(() => {
        if (group_id) {
            if (!room_id) {
                const id = api_hatch.fetchPrimaryRoom(group_id);
                if (validate(id)) {
                    navigate(`/${group_id}/${room_id}`);
                } else {
                    console.log("404 not found, this group might not have any open rooms!");
                    return;
                    //404 not found, this group might not have any open rooms!
                }
            } else {
                if (context_data.current_group.current) {
                    if (context_data.current_group.current.id !== group_id) {
                        api_hatch.fetchGroup(group_id, room_id);
                        //setting current group, preferrably in fetchGroup()
                    } else {
                        api_hatch.fetchMessages(group_id, room_id);
                        //setting current room, preferrably in fetchMessages()
                    }
                } else api_hatch.fetchGroup(group_id, room_id);
                //setting current group, preferrably in fetchGroup()
            }

        } else {
            return;
            //404 not found page!
        }
    }, []);

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
                <div id={styles.toContacts}>
                    <div id={styles.toContactsShrunk}></div>
                </div>
                <hr className={styles.divisionLine}></hr>
                        
                {groups_array.map(group => (
                    <div className={styles.group} key={group.id} onClick={() => navigate(context_data.main_path.current + group.id)}>
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