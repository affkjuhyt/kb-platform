import { DataSource, DataSourceCreateRequest, DataSourceUpdateRequest, SyncStats, DataSourceType, DataSourceStatus, AuthType, StorageProvider } from '@/types/data-source';

// TODO: Replace mock data with actual API calls before production deployment
// When implementing real API integration:
// 1. Uncomment axios import and configure BASE_PATH
// 2. Replace Promise-based mock returns with actual axios calls
// 3. Implement secure credential handling for API keys and storage credentials

// import axios from 'axios';
// const BASE_PATH = '/api/data-sources';

// Mock data for development
const MOCK_DATA_SOURCES: DataSource[] = [
    {
        id: 'ds-1',
        kb_id: 'kb-1',
        type: DataSourceType.WEB_CRAWLER,
        name: 'Documentation Crawler',
        config: {
            url: 'https://docs.example.com',
            depth: 3,
            include_patterns: ['/docs/*', '/api/*'],
            exclude_patterns: ['/blog/*'],
            schedule: '0 0 * * *', // Daily at midnight
            user_agent: 'KnowledgeBot/1.0',
            rate_limit: 2,
            respect_robots_txt: true,
        },
        status: DataSourceStatus.ACTIVE,
        last_sync: new Date(Date.now() - 86400000).toISOString(),
        next_sync: new Date(Date.now() + 3600000).toISOString(),
        created_at: new Date(Date.now() - 86400000 * 7).toISOString(),
        updated_at: new Date(Date.now() - 86400000).toISOString(),
    },
    {
        id: 'ds-2',
        kb_id: 'kb-1',
        type: DataSourceType.API_CONNECTOR,
        name: 'Support Tickets API',
        config: {
            endpoint: 'https://api.support.example.com/tickets',
            method: 'GET',
            auth_type: AuthType.API_KEY,
            api_key: '***hidden***',
            headers: {
                'Accept': 'application/json',
            },
            response_mapping: '$.data[*]',
            pagination: {
                type: 'offset',
                param_name: 'offset',
            },
        },
        status: DataSourceStatus.SYNCING,
        last_sync: new Date(Date.now() - 3600000).toISOString(),
        next_sync: null,
        created_at: new Date(Date.now() - 86400000 * 14).toISOString(),
        updated_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
        id: 'ds-3',
        kb_id: 'kb-1',
        type: DataSourceType.FILE_WATCHER,
        name: 'S3 Documents Bucket',
        config: {
            provider: StorageProvider.S3,
            bucket: 'company-documents',
            path_pattern: 'knowledge-base/**/*.pdf',
            access_key: '***hidden***',
            secret_key: '***hidden***',
            sync_interval: 60,
            include_extensions: ['pdf', 'docx', 'txt'],
        },
        status: DataSourceStatus.ERROR,
        last_sync: new Date(Date.now() - 7200000).toISOString(),
        next_sync: new Date(Date.now() + 1800000).toISOString(),
        created_at: new Date(Date.now() - 86400000 * 30).toISOString(),
        updated_at: new Date(Date.now() - 7200000).toISOString(),
    },
];

const MOCK_SYNC_STATS: Record<string, SyncStats> = {
    'ds-1': {
        last_sync: new Date(Date.now() - 86400000).toISOString(),
        next_sync: new Date(Date.now() + 3600000).toISOString(),
        documents_synced: 245,
        documents_failed: 3,
        queue_depth: 12,
        errors: [
            {
                timestamp: new Date(Date.now() - 86400000).toISOString(),
                message: 'Failed to crawl /api/deprecated',
                details: '404 Not Found',
            },
        ],
    },
    'ds-2': {
        last_sync: new Date(Date.now() - 3600000).toISOString(),
        next_sync: null,
        documents_synced: 89,
        documents_failed: 0,
        queue_depth: 45,
        errors: [],
    },
    'ds-3': {
        last_sync: new Date(Date.now() - 7200000).toISOString(),
        next_sync: new Date(Date.now() + 1800000).toISOString(),
        documents_synced: 156,
        documents_failed: 8,
        queue_depth: 0,
        errors: [
            {
                timestamp: new Date(Date.now() - 7200000).toISOString(),
                message: 'Access denied to bucket',
                details: 'Invalid credentials or insufficient permissions',
            },
        ],
    },
};

export const dataSourceApi = {
    /**
     * List all data sources for a knowledge base
     */
    list: async (kbId: string): Promise<DataSource[]> => {
        // TODO: Replace with actual API call
        // return axios.get(`${BASE_PATH}?kb_id=${kbId}`).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 300));
        return MOCK_DATA_SOURCES.filter(ds => ds.kb_id === kbId);
    },

    /**
     * Get a single data source by ID
     */
    get: async (sourceId: string): Promise<DataSource> => {
        // TODO: Replace with actual API call
        // return axios.get(`${BASE_PATH}/${sourceId}`).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 200));
        const source = MOCK_DATA_SOURCES.find(ds => ds.id === sourceId);
        if (!source) throw new Error('Data source not found');
        return source;
    },

    /**
     * Create a new data source
     */
    create: async (data: DataSourceCreateRequest): Promise<DataSource> => {
        // TODO: Replace with actual API call
        // return axios.post(BASE_PATH, data).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 500));
        const newSource: DataSource = {
            id: `ds-${crypto.randomUUID()}`,
            kb_id: data.kb_id,
            type: data.type,
            name: data.name,
            config: data.config,
            status: DataSourceStatus.PAUSED,
            last_sync: null,
            next_sync: null,
            created_at: new Date().toISOString(),
            updated_at: null,
        };
        MOCK_DATA_SOURCES.push(newSource);
        return newSource;
    },

    /**
     * Update a data source
     */
    update: async (sourceId: string, data: DataSourceUpdateRequest): Promise<DataSource> => {
        // TODO: Replace with actual API call
        // return axios.patch(`${BASE_PATH}/${sourceId}`, data).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 400));
        const source = MOCK_DATA_SOURCES.find(ds => ds.id === sourceId);
        if (!source) throw new Error('Data source not found');

        if (data.name) source.name = data.name;
        if (data.config) source.config = { ...source.config, ...data.config };
        source.updated_at = new Date().toISOString();

        return source;
    },

    /**
     * Delete a data source
     */
    delete: async (sourceId: string): Promise<void> => {
        // TODO: Replace with actual API call
        // return axios.delete(`${BASE_PATH}/${sourceId}`);

        await new Promise(resolve => setTimeout(resolve, 300));
        const index = MOCK_DATA_SOURCES.findIndex(ds => ds.id === sourceId);
        if (index !== -1) {
            MOCK_DATA_SOURCES.splice(index, 1);
        }
    },

    /**
     * Pause a data source
     */
    pause: async (sourceId: string): Promise<DataSource> => {
        // TODO: Replace with actual API call
        // return axios.post(`${BASE_PATH}/${sourceId}/pause`).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 200));
        const source = MOCK_DATA_SOURCES.find(ds => ds.id === sourceId);
        if (!source) throw new Error('Data source not found');

        source.status = DataSourceStatus.PAUSED;
        source.next_sync = null;
        source.updated_at = new Date().toISOString();

        return source;
    },

    /**
     * Resume a data source
     */
    resume: async (sourceId: string): Promise<DataSource> => {
        // TODO: Replace with actual API call
        // return axios.post(`${BASE_PATH}/${sourceId}/resume`).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 200));
        const source = MOCK_DATA_SOURCES.find(ds => ds.id === sourceId);
        if (!source) throw new Error('Data source not found');

        source.status = DataSourceStatus.ACTIVE;
        source.next_sync = new Date(Date.now() + 3600000).toISOString();
        source.updated_at = new Date().toISOString();

        return source;
    },

    /**
     * Manually trigger a sync
     */
    triggerSync: async (sourceId: string): Promise<DataSource> => {
        // TODO: Replace with actual API call
        // return axios.post(`${BASE_PATH}/${sourceId}/sync`).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 300));
        const source = MOCK_DATA_SOURCES.find(ds => ds.id === sourceId);
        if (!source) throw new Error('Data source not found');

        source.status = DataSourceStatus.SYNCING;
        source.updated_at = new Date().toISOString();

        return source;
    },

    /**
     * Get sync statistics for a data source
     */
    getStats: async (sourceId: string): Promise<SyncStats> => {
        // TODO: Replace with actual API call
        // return axios.get(`${BASE_PATH}/${sourceId}/stats`).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 200));
        return MOCK_SYNC_STATS[sourceId] || {
            last_sync: null,
            next_sync: null,
            documents_synced: 0,
            documents_failed: 0,
            queue_depth: 0,
            errors: [],
        };
    },
};
