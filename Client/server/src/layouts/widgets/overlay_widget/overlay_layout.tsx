import React from "react";
import ModalView from './views/modal_view';
import ErrorView from './views/error_view';

const OverlayLayout: React.FC = () => {
    return (
        <>
            <ModalView />
            <ErrorView />
        </>
    );
};

export default React.memo(OverlayLayout);