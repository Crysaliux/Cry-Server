import React from "react";
import { useContext } from "react";
import { CoreGlobalContext } from "services/core";
import { APIHatch } from "services/api_listener";
import { useNavigate, useParams } from "react-router-dom";
import { Outlet } from "react-router-dom";
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
    const navigate = useNavigate();

    const { group_id, room_id } = useParams();

    if (!context_data.current_group.current) {
        if (group_id) {
            if (room_id) api_hatch.fetchGroup(group_id, room_id);
            else api_hatch.fetchGroup(group_id, null); //will fix, fetchPromaryRoom => room_id (string)
        } else {
            //404 not found page!
        }
    }

    const groups = useGroups();
    const rooms = useRooms();
    const spaces = useSpaces();

    const groups_array = Object.values(groups);
    const rooms_array = Object.values(rooms);
    const spaces_array = Object.values(spaces);

    const orphan_rooms = rooms_array.filter((room) => room.space_id === null);
    const FetchChildRooms = (space_id: string) => {
        return rooms_array.filter((room) => room.space_id === space_id);
    };

    return (
        <>
            <div id="header">
                <div id="header-buffer"></div>
                <div id="channel-name">
                    Channel name
                </div>
                <div id="manage-members">
                    <div id="invite">

                    </div>
                    <div id="sort-by">
                        <div id="sort-by-arrow"></div>
                        Roles
                    </div>
                    <div id="hide-members">

                    </div>
                </div>
            </div>
                    
            <div id="groups">
                <div id="to-contacts">
                    <div id="to-contacts-shrunk"></div>
                </div>
                <hr className="division_line"></hr>
                        
                {groups_array.map(group => (
                    <div className="group" key={group.id}>
                        <div className="group_shrunk"></div>
                    </div>
                ))}

                <hr className="division_line"></hr>
                <div id="create-group">
                    <div id="create-group-shrunk"></div>
                </div>
            </div>

            <div id="rooms">
                <div id="actions">
                    <div id="group-header">
                        Group name
                        <div id="settings"></div>
                    </div>
                    <div className="action">Add room</div>
                    <div className="action">Add space</div>
                </div>
                <hr className="division_line"></hr>
                {orphan_rooms.map(room => (
                    <div className="room" key={room.id}>
                        <div className="hashtag">#</div>{ room.name }
                    </div>
                ))}
                {spaces_array.map(space => (
                    <div className="space" key={space.id}>
                        <div className="space_name">{ space.name }</div>
                        {FetchChildRooms(space.id).map(room => (
                            <div className="room" key={room.id}>
                                <div className="hashtag">#</div>{ room.name }
                            </div>
                        ))}
                    </div>
                ))}
            </div>
            <Outlet />
        </>
    );
};

export default React.memo(GroupLayout);