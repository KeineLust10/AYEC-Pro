import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const API_URL =
    process.env.EXPO_PUBLIC_API_URL ||
    'https://panel.ayecpro.com/api';

const client = axios.create({
    baseURL: API_URL,
    timeout: 15000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Attach JWT Bearer token to every request
client.interceptors.request.use(
    async (config) => {
        try {
            const token = await SecureStore.getItemAsync('userToken');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        } catch (_) {
            // Storage read failed -- proceed without token
        }
        return config;
    },
    (error) => Promise.reject(error),
);

// Handle 401 globally: clear token so the app redirects to login
client.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response && error.response.status === 401) {
            await SecureStore.deleteItemAsync('userToken');
        }
        return Promise.reject(error);
    },
);

export default client;
