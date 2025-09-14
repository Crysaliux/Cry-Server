import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

import "static/global.css";
import "static/group.css";
import "static/login.css";
import "static/signup.css";
import "static/main_page.css";
import "react-day-picker/style.css";


createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <App />
    </StrictMode>
);