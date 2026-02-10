// import axios from 'axios';
import { KnowledgeBase, KBCreateRequest } from '@/types/knowledge-base';

// const BASE_PATH = '/api/kb';

// Mock data for development
const MOCK_KBS: KnowledgeBase[] = [
    {
        id: 'kb-1',
        name: 'Technical Documentation',
        description: 'Internal documentation for the platform architecture and API.',
        tenant_id: 'tenant-1',
        embedding_model: 'text-embedding-3-small',
        document_count: 124,
        chunk_count: 1240,
        created_at: new Date(Date.now() - 86400000 * 7).toISOString(),
        updated_at: new Date(Date.now() - 86400000).toISOString(),
    },
    {
        id: 'kb-2',
        name: 'Customer Support Wiki',
        description: 'Knowledge base for support agents to resolve common issues.',
        tenant_id: 'tenant-1',
        embedding_model: 'text-embedding-3-small',
        document_count: 56,
        chunk_count: 450,
        created_at: new Date(Date.now() - 86400000 * 30).toISOString(),
        updated_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    }
];

export const kbApi = {
    list: async (): Promise<KnowledgeBase[]> => {
        // For now, return mock data since backend might not be ready
        // In a real scenario, this would be:
        // const response = await axios.get<KnowledgeBase[]>(BASE_PATH);
        // return response.data;
        return new Promise((resolve) => {
            setTimeout(() => resolve(MOCK_KBS), 500);
        });
    },

    get: async (id: string): Promise<KnowledgeBase> => {
        return new Promise((resolve, reject) => {
            const kb = MOCK_KBS.find(k => k.id === id);
            setTimeout(() => {
                if (kb) resolve(kb);
                else reject(new Error('KB not found'));
            }, 500);
        });
    },

    create: async (data: KBCreateRequest): Promise<KnowledgeBase> => {
        const newKb: KnowledgeBase = {
            id: `kb-${Math.random().toString(36).substr(2, 9)}`,
            name: data.name,
            description: data.description || null,
            tenant_id: 'default',
            embedding_model: data.embedding_model || 'text-embedding-3-small',
            document_count: 0,
            chunk_count: 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };

        return new Promise((resolve) => {
            setTimeout(() => resolve(newKb), 800);
        });
    },

    delete: async (_id: string): Promise<void> => {
        return new Promise((resolve) => {
            setTimeout(resolve, 500);
        });
    }
};
