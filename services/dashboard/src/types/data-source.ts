export enum DataSourceType {
    WEB_CRAWLER = 'web_crawler',
    API_CONNECTOR = 'api_connector',
    FILE_WATCHER = 'file_watcher',
}

export enum DataSourceStatus {
    ACTIVE = 'active',
    PAUSED = 'paused',
    ERROR = 'error',
    SYNCING = 'syncing',
}

export enum AuthType {
    NONE = 'none',
    API_KEY = 'api_key',
    BEARER_TOKEN = 'bearer_token',
    OAUTH = 'oauth',
}

export enum StorageProvider {
    S3 = 's3',
    GCS = 'gcs',
}

export interface WebCrawlerConfig {
    url: string;
    depth: number;
    include_patterns?: string[];
    exclude_patterns?: string[];
    schedule?: string; // cron expression
    user_agent?: string;
    rate_limit?: number; // requests per second
    respect_robots_txt?: boolean;
}

export interface APIConnectorConfig {
    endpoint: string;
    method: 'GET' | 'POST';
    auth_type: AuthType;
    api_key?: string;
    bearer_token?: string;
    oauth_config?: Record<string, unknown>;
    headers?: Record<string, string>;
    response_mapping?: string; // JSON path
    pagination?: {
        type: 'offset' | 'cursor' | 'page';
        param_name: string;
    };
}

export interface FileWatcherConfig {
    provider: StorageProvider;
    bucket: string;
    path_pattern: string;
    access_key?: string;
    secret_key?: string;
    service_account_json?: string;
    sync_interval: number; // minutes
    include_extensions?: string[];
    exclude_patterns?: string[];
}

export type DataSourceConfig = WebCrawlerConfig | APIConnectorConfig | FileWatcherConfig;

export interface DataSource {
    id: string;
    kb_id: string;
    type: DataSourceType;
    name: string;
    config: DataSourceConfig;
    status: DataSourceStatus;
    last_sync: string | null;
    next_sync: string | null;
    created_at: string;
    updated_at: string | null;
}

export interface SyncStats {
    last_sync: string | null;
    next_sync: string | null;
    documents_synced: number;
    documents_failed: number;
    queue_depth: number;
    errors: SyncError[];
}

export interface SyncError {
    timestamp: string;
    message: string;
    details?: string;
}

export interface DataSourceCreateRequest {
    kb_id: string;
    type: DataSourceType;
    name: string;
    config: DataSourceConfig;
}

export interface DataSourceUpdateRequest {
    name?: string;
    config?: Partial<DataSourceConfig>;
}
