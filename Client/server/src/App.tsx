import React from 'react';
import { Listener } from 'services/listener';
import './App.css'

const App: React.FC = () => (
    <Listener addr="ws://somehost">
        <div id="container">
            <div id="overlays">
                <div id="client-overlay"></div>
                <div id="modal-overlay"></div>
            </div>
            <div id="widgets">
                <div id="header-widget" className="widget"></div>
                <div id="groups-widget" className="widget"></div>
                <div id="channels-contacts-widget" className="widget"></div>
                <div id="chat-widget" className="widget"></div>
                <div id="members-contact-widget" className="widget"></div>
                <div id="member-info-popup-widget" className="popup-widget"></div>
                <div id="client-info-popup-widget" className="popup-widget"></div>
                <div id="channel-settings-popup-widget" className="popup-widget"></div>
                <div id="group-settings-popup-widget" className="popup-widget"></div>
            </div>
        </div>
    </Listener>
);

export default App;