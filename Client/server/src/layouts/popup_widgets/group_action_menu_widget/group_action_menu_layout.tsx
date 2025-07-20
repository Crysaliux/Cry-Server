import React, { useContext, useEffect, useRef, useState } from "react";
import { GlobalContext } from "services/core";
import GroupActionMenuView from './views/group_action_menu_view';

interface CursorPosition {
    cursor_x: number;
    cursor_y: number;
}

const GroupActionMenuLayout: React.FC = () => {
    const context_data = useContext(GlobalContext);
    if (!context_data) {
        throw new Error("Context for channels_view can't be defined.");
    }
    const MenuReference = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const HandleOutsideClick = (event: MouseEvent) => {
            const target = event.target as HTMLElement
            if (target.id !== 'group-info-widget' && target.id !== 'group-info-widget-name') {
                if (MenuReference.current && !MenuReference.current.contains(event.target as Node)) {
                    context_data.SetGroupActionMenuDisplayStatus(false);
                }
            }
        };

        document.addEventListener('mousedown', HandleOutsideClick);
        return () => {
            document.removeEventListener('mousedown', HandleOutsideClick);
        };
    }, [])

    return (
        <>
            {
                context_data.group_action_menu_display_status ?
                <div ref={MenuReference} id="group-action-menu-popup-widget" className="popup-widget border">
                    <GroupActionMenuView />
                </div>
                : null
            }
        </>
    );
};

export default React.memo(GroupActionMenuLayout);