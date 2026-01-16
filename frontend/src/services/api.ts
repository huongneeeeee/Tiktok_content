/**
 * API Service - Centralized API configuration
 */
import axios from 'axios';

// Get API URL from environment or use default
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance with default config
export const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor for logging
api.interceptors.request.use(
    (config) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
    },
    (error) => {
        console.error('[API] Request error:', error);
        return Promise.reject(error);
    }
);

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('[API] Response error:', error.response?.data || error.message);
        return Promise.reject(error);
    }
);

// API Functions
export const healthCheck = async () => {
    const response = await api.get('/health');
    return response.data;
};

export const dbTest = async () => {
    const response = await api.get('/db/test');
    return response.data;
};

export const dbStats = async () => {
    const response = await api.get('/db/stats');
    return response.data;
};

export default api;
