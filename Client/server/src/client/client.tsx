import React from "react";
import { useState } from "react";

function Client({ id, name, username, groups, contacts }) {
    const [ClientName, ChangeClientName] = useState(name);
    const [ClientUsername, ChangeClientUsername] = useState(username);
    const [ClientGroups, EditClientGroups] = useState(groups);
    const [ClientContacts, EditClientContacts] = useState(contacts);

    return (
        <div>
            ???
        </div>
    );
}