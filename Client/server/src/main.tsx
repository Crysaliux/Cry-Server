import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

import "static/global.css";

//<StrictMode>
createRoot(document.getElementById('root')!).render(

        <App />
    
);