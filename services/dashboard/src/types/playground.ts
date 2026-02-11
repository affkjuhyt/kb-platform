// Search Playground Types
export interface SearchQuery {
    query: string;
    kb_id: string;
    top_k?: number;
    similarity_threshold?: number;
    filters?: Record<string, unknown>;
}

export interface SearchResult {
    id: string;
    content: string;
    score: number;
    metadata: {
        document_id: string;
        document_name: string;
        chunk_index: number;
        source: string;
        created_at: string;
    };
    highlights?: string[];
}

export interface SearchResponse {
    results: SearchResult[];
    total: number;
    query_time_ms: number;
}

// RAG Playground Types
export interface RAGQuery {
    query: string;
    kb_id: string;
    system_prompt?: string;
    model?: string;
    temperature?: number;
    max_tokens?: number;
    top_k?: number;
}

export interface Citation {
    index: number;
    document_id: string;
    document_name: string;
    chunk_content: string;
    score: number;
}

export interface RAGResponse {
    answer: string;
    citations: Citation[];
    model: string;
    tokens_used: number;
    response_time_ms: number;
}

// Prompt Templates
export interface PromptTemplate {
    id: string;
    name: string;
    description: string;
    category: 'general' | 'technical' | 'creative' | 'analytical';
    content: string;
    variables: string[];
    created_at: string;
}

export interface SavedPrompt {
    id: string;
    name: string;
    content: string;
    kb_id?: string;
    created_at: string;
    updated_at: string;
}

// Compare Mode Types
export interface ComparisonQuery {
    query: string;
    kb_id: string;
    models: string[];
    system_prompt?: string;
    temperature?: number;
    top_k?: number;
}

export interface ComparisonResult {
    model: string;
    answer: string;
    citations: Citation[];
    tokens_used: number;
    response_time_ms: number;
}

export interface ComparisonResponse {
    query: string;
    results: ComparisonResult[];
    total_time_ms: number;
}

// Playground Settings
export interface PlaygroundSettings {
    default_kb_id?: string;
    default_model?: string;
    default_temperature?: number;
    default_top_k?: number;
    auto_save_prompts?: boolean;
}
