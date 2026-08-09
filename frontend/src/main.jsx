import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './auth';
import './styles.css';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* The app is served from Tomcat under /enotes, so the router's paths are
        relative to that context path rather than the domain root. */}
    <BrowserRouter basename="/enotes">
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
