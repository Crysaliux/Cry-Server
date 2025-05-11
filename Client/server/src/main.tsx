import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './static/global_styles.css';
import './static/client_interface.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
      <App />
  </StrictMode>
);