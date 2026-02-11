import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { toast } from 'sonner';

/**
 * Shared API client with JWT auth injection and error handling.
 * All requests go through Next.js rewrite: /api/* → API Gateway
 */
const apiClient = axios.create({
    baseURL: '/api',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// ─── Auth Token Management ────────────────────────────────────────────

const TOKEN_KEY = 'access_token';
const TENANT_KEY = 'tenant_id';

export function setAuthToken(token: string, tenantId: string) {
    if (typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, token);
        localStorage.setItem(TENANT_KEY, tenantId);
    }
}

export function getAuthToken(): string | null {
    if (typeof window !== 'undefined') {
        return localStorage.getItem(TOKEN_KEY);
    }
    return null;
}

export function getTenantId(): string | null {
    if (typeof window !== 'undefined') {
        return localStorage.getItem(TENANT_KEY);
    }
    return null;
}

export function clearAuth() {
    if (typeof window !== 'undefined') {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(TENANT_KEY);
    }
}

// ─── Request Interceptor ──────────────────────────────────────────────

apiClient.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = getAuthToken();
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// ─── Response Interceptor ─────────────────────────────────────────────

apiClient.interceptors.response.use(
    (response) => response,
    (error: AxiosError<{ detail?: string }>) => {
        const status = error.response?.status;
        const detail = error.response?.data?.detail || error.message;

        switch (status) {
            case 401:
                clearAuth();
                if (typeof window !== 'undefined') {
                    toast.error('Session expired. Please log in again.');
                    window.location.href = '/login';
                }
                break;
            case 403:
                toast.error('You do not have permission to perform this action.');
                break;
            case 429:
                toast.error('Rate limit exceeded. Please wait and try again.');
                break;
            case 502:
            case 503:
                toast.error('Service temporarily unavailable. Please try again later.');
                break;
            default:
                if (!error.response) {
                    toast.error('Network error. Please check your connection.');
                } else if (status && status >= 500) {
                    toast.error(`Server error: ${detail}`);
                }
        }

        return Promise.reject(error);
    }
);

export { apiClient };
export default apiClient;
