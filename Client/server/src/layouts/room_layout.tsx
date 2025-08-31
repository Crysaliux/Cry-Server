import React from "react";

const RoomLayout: React.FC = () => {
    return (
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
    );
};

export default React.memo(RoomLayout);