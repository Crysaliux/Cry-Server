import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

import "static/global.css";
import "static/group.css";
import "static/login.css";
import "static/sign_up.css";
import "static/main_page.css";


createRoot(document.getElementById('root')!).render(
  <StrictMode>
      <App />
  </StrictMode>
);