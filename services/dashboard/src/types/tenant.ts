export interface Tenant {
    id: string;
    name: string;
    description?: string;
    plan: string;
    owner_id: string;
    created_at: string;
    updated_at: string;
}

export interface TenantCreate {
    name: string;
    description?: string;
    plan: string;
}

export interface TenantUpdate {
    name?: string;
    description?: string;
    plan?: string;
}

export interface TenantSettings {
    tenant_id: string;
    rate_limit: {
        requests_per_minute: number;
        requests_per_day: number;
    };
    quotas: {
        max_documents: number;
        max_storage_gb: number;
        max_users: number;
    };
    api_keys_enabled: boolean;
    updated_at: string;
}

export interface TenantSettingsUpdate {
    rate_limit?: {
        requests_per_minute?: number;
        requests_per_day?: number;
    };
    quotas?: {
        max_documents?: number;
        max_storage_gb?: number;
        max_users?: number;
    };
    api_keys_enabled?: boolean;
}

export interface TenantUser {
    user_id: string;
    email: string;
    name: string;
    role: 'owner' | 'admin' | 'member' | 'viewer';
    joined_at: string;
}

export interface UserInvite {
    email: string;
    role: 'owner' | 'admin' | 'member' | 'viewer';
    name?: string;
}
