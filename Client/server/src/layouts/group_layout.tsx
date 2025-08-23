import React from "react";
import { Outlet } from "react-router-dom";
import { 
    useGroups, 
    useMessages, 
    usePermissionsTable, 
    useRoles, 
    useRooms, 
    useSpaces,
    useMembers,
} from "services/worker";


const GroupLayout: React.FC = () => {
    const groups = useGroups();
    const rooms = useRooms();
    const spaces = useSpaces();

    const orphan_rooms = rooms.filter((room) => room.space_id === null);
    const FetchChildRooms = (space_id: string) => {
        return rooms.filter((room) => room.space_id === space_id);
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
                        
                {groups.map(group => (
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
                {spaces.map(space => (
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