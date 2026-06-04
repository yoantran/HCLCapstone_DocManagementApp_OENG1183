import axios from 'axios';

import { API_BASE_URL } from '../constants';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json'
    },
    timeout: 10000 // 10 seconds
});

api.interceptors.request.use(
    async (config) => {
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');

        if (token) {
            config.headers["Authorization"] = `Bearer ${token}`;
        }

        return config;
    },
    (error) => {
        console.error("Request Error: ", error);
        return Promise.reject(error);
    }
);

api.interceptors.response.use(
    (res) => {
        return res;
    },
    (error) => {
        if (error?.response?.status === 403) {
            // Role insufficient — let the router's ProtectedRoute handle UI,
            // but you can dispatch a global toast here later
            console.warn('403 Forbidden');
        }
        if (error?.response?.status === 401) {
            // Token expired — clear storage and hard-redirect
            localStorage.removeItem('token');
            window.location.href = '/login';
        }
        throw error;
    }
);

export default api;