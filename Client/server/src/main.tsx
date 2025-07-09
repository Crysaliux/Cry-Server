import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import 'static/contacts_interface.css';
import 'static/group_interface.css';
import 'static/global_interface.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
      <App />
  </StrictMode>
);