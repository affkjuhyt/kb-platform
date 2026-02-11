import apiClient from './client';
import { KnowledgeBase, KBCreateRequest } from '@/types/knowledge-base';

/**
 * Knowledge Base API client.
 * 
 * Since the backend treats tenants as knowledge base containers (one tenant = one KB),
 * KB operations map to tenant management endpoints.
 * For now, we use the tenants API and maintain local mock data as fallback.
 */
export const kbApi = {
    /**
     * List all knowledge bases (tenants) accessible to the current user
     * GET /tenants
     */
    list: async (): Promise<KnowledgeBase[]> => {
        try {
            const response = await apiClient.get('/tenants');
            // Map tenant data to KB format
            return response.data.map((tenant: Record<string, unknown>) => ({
                id: tenant.id || tenant.tenant_id,
                name: tenant.name || `Tenant ${tenant.id}`,
                description: tenant.description || null,
                tenant_id: tenant.id || tenant.tenant_id,
                embedding_model: tenant.embedding_model || 'text-embedding-3-small',
                document_count: tenant.document_count || 0,
                chunk_count: tenant.chunk_count || 0,
                created_at: tenant.created_at || new Date().toISOString(),
                updated_at: tenant.updated_at || null,
            }));
        } catch (error) {
            console.error('Failed to fetch knowledge bases, falling back to empty list:', error);
            return [];
        }
    },

    /**
     * Get a single knowledge base by ID
     * GET /tenants/:id
     */
    get: async (id: string): Promise<KnowledgeBase> => {
        const response = await apiClient.get(`/tenants/${id}`);
        const tenant = response.data;
        return {
            id: tenant.id || tenant.tenant_id,
            name: tenant.name || `Tenant ${tenant.id}`,
            description: tenant.description || null,
            tenant_id: tenant.id || tenant.tenant_id,
            embedding_model: tenant.embedding_model || 'text-embedding-3-small',
            document_count: tenant.document_count || 0,
            chunk_count: tenant.chunk_count || 0,
            created_at: tenant.created_at || new Date().toISOString(),
            updated_at: tenant.updated_at || null,
        };
    },

    /**
     * Create a new knowledge base (tenant)
     * POST /tenants
     */
    create: async (data: KBCreateRequest): Promise<KnowledgeBase> => {
        const response = await apiClient.post('/tenants', {
            name: data.name,
            description: data.description,
            embedding_model: data.embedding_model || 'text-embedding-3-small',
        });
        const tenant = response.data;
        return {
            id: tenant.id || tenant.tenant_id,
            name: tenant.name || data.name,
            description: tenant.description || data.description || null,
            tenant_id: tenant.id || tenant.tenant_id,
            embedding_model: tenant.embedding_model || data.embedding_model || 'text-embedding-3-small',
            document_count: 0,
            chunk_count: 0,
            created_at: tenant.created_at || new Date().toISOString(),
            updated_at: null,
        };
    },

    /**
     * Delete a knowledge base (tenant)
     * DELETE /tenants/:id
     */
    delete: async (id: string): Promise<void> => {
        await apiClient.delete(`/tenants/${id}`);
    },
};
