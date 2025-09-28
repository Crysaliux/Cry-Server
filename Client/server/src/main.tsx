import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

import "static/global.css";
import "static/group.css";
import "static/login.css";
import "static/signup.css";
import "static/main_page.css";
import "static/loading.css";
import "react-day-picker/style.css";

//<StrictMode>
createRoot(document.getElementById('root')!).render(

        <App />
    
);