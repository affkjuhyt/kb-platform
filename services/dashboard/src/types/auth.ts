export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export interface User {
    id: string;
    email: string;
    full_name?: string;
    role: string;
    tenant_id: string;
}
