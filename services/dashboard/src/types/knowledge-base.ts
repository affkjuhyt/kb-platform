export interface KnowledgeBase {
    id: string;
    name: string;
    description: string | null;
    tenant_id: string;
    embedding_model: string;
    document_count: number;
    chunk_count: number;
    created_at: string;
    updated_at: string | null;
}

export interface KBCreateRequest {
    name: string;
    description?: string;
    embedding_model?: string;
}

export interface KBStats {
    document_count: number;
    chunk_count: number;
    query_volume_24h: number;
    avg_latency_ms: number;
}
