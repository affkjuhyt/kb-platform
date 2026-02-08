import axios from 'axios';
import {
    Tenant,
    TenantCreate,
    TenantUpdate,
    TenantSettings,
    TenantSettingsUpdate,
    TenantUser,
    UserInvite
} from '@/types/tenant';

// Base URL is handled by Next.js rewrite in development
// In production, this should point to the API Gateway.
// We need to use the proxy path because direct calls to localhost:8080 
// from client-side might fail CORS if not configured, or we can use the Next.js rewrite.

// However, standard Next.js proxying usually involves `next.config.js` rewrites.
// Let's assume `/tenants` maps to API Gateway `/tenants`.

const BASE_PATH = '/api/tenants';

export const tenantApi = {
    // Tenant CRUD
    list: async (): Promise<Tenant[]> => {
        const response = await axios.get<Tenant[]>(BASE_PATH);
        return response.data;
    },

    create: async (data: TenantCreate): Promise<Tenant> => {
        const response = await axios.post<Tenant>(BASE_PATH, data);
        return response.data;
    },

    get: async (id: string): Promise<Tenant> => {
        const response = await axios.get<Tenant>(`${BASE_PATH}/${id}`);
        return response.data;
    },

    update: async (id: string, data: TenantUpdate): Promise<Tenant> => {
        const response = await axios.put<Tenant>(`${BASE_PATH}/${id}`, data);
        return response.data;
    },

    delete: async (id: string): Promise<void> => {
        await axios.delete(`${BASE_PATH}/${id}`);
    },

    // Settings
    getSettings: async (id: string): Promise<TenantSettings> => {
        const response = await axios.get<TenantSettings>(`${BASE_PATH}/${id}/settings`);
        return response.data;
    },

    updateSettings: async (id: string, data: TenantSettingsUpdate): Promise<TenantSettings> => {
        const response = await axios.put<TenantSettings>(`${BASE_PATH}/${id}/settings`, data);
        return response.data;
    },

    // Users
    listUsers: async (id: string): Promise<TenantUser[]> => {
        const response = await axios.get<TenantUser[]>(`${BASE_PATH}/${id}/users`);
        return response.data;
    },

    inviteUser: async (id: string, data: UserInvite): Promise<TenantUser> => {
        const response = await axios.post<TenantUser>(`${BASE_PATH}/${id}/users/invite`, data);
        return response.data;
    },

    removeUser: async (tenantId: string, userId: string): Promise<void> => {
        await axios.delete(`${BASE_PATH}/${tenantId}/users/${userId}`);
    },
};
