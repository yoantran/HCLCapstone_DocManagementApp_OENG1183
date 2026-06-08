import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';

import { AuthProvider } from './context/AuthContext';
import App from "./App.jsx";
import {ToastContainer} from "react-toastify";

createRoot(document.getElementById('root')).render(
    <>
        <StrictMode>
            <ToastContainer
                autoClose={3000}
                hideProgressBar
                closeButton={false}
                position={"bottom-left"}
                newestOnTop
                pauseOnFocusLoss={false}
                style={{ fontFamily: "inherit" }}
            />
            <AuthProvider>
                <App />
            </AuthProvider>
        </StrictMode>
    </>
);