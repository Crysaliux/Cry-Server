import React from "react";
import AddFriendView from '../add_friend_view';
import ContactsActionBarView from '../contacts_action_bar_view';
import { Outlet } from "react-router-dom";

const ContactsLayout: React.FC = () => {

    return (
        <>
            <div id="header-widget" className="silent_widget">
                <div id="header-support-widget" className="widget">

                </div>
                <div id="header-group-addfriend-widget" className="widget">
                    <AddFriendView />
                </div>
                <div id="header-channelinfo-contacts-widget" className="widget">
                    <ContactsActionBarView />
                </div>
                <div id="header-memberstats-widget" className="widget">

                </div>
            </div>

            <div id="channels-contacts-widget" className="widget">
                
            </div>

            <div id="chat-widget" className="widget">
                <Outlet />
            </div>

            <div id="members-contact-widget" className="widget">

            </div>
        </>
    );
};

export default React.memo(ContactsLayout);