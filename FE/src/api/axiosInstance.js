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
            // Handle forbidden error
        }
        if (error?.response?.status === 401) {
            // Handle unauthorized error (e.g., log out the user)
        }
        throw error;
    }
);

export default api;