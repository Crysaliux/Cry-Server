import React from "react";
import { 
    useGroups, 
    useMessages, 
    usePermissions, 
    useRoles, 
    useRooms, 
    useSpaces 
} from "services/worker";

const GroupLayout: React.FC = () => {
    const groups = useGroups();
    const messages = useSpaces();
    const permissions = usePermissions();
    const roles = useRoles();
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
                    
            <div id="chat">
                <div id="messages">
                    
                    <div className="message">
                        <div className="avatar"></div>
                        <div className="body">
                            <div className="nickname">Nickname</div>
                            <div className="content">
                                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vestibulum vel nunc fringilla, ullamcorper quam in, hendrerit mi. Duis commodo malesuada nulla, ut consequat sem euismod ut. Curabitur vel magna tempor, volutpat dolor nec, molestie lectus. Nullam egestas commodo vulputate. Ut iaculis neque erat, id maximus nunc pellentesque sed. Etiam at sapien et erat vulputate mattis nec nec tortor. Praesent suscipit blandit dui, ac interdum magna efficitur at. In quis elementum nisl, a imperdiet tortor. Aenean consectetur, elit sit amet varius porttitor, turpis dolor congue nunc, in consequat urna urna id sem. Donec ut lacus urna. Pellentesque condimentum arcu dignissim ex bibendum sodales. Sed tristique, dolor aliquam ultrices eleifend, felis tellus suscipit elit, quis efficitur urna ex nec ligula. Phasellus quis tortor in nunc hendrerit tempus id in urna. Mauris ultrices non lorem at malesuada.

                                Aliquam vitae massa accumsan, pellentesque magna eget, faucibus elit. Morbi plac
                            </div>
                        </div>
                    </div>

                    <div className="additional_message">
                        <div className="buffer"></div>
                        <div className="body">
                            <div className="content">
                                Lorem ipsum dolor sit amet, consectetur adipi
                            </div>
                        </div>
                    </div>

                </div>

                <div id="chatarea">
                    <div id="attachement"></div>
                    <textarea autoFocus id="chatbar"></textarea>
                </div>

            </div>
        </>
    );
};

export default React.memo(GroupLayout);