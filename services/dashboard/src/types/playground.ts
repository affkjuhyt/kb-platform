// ─── Backend-aligned Types ────────────────────────────────────────────
// These types mirror the Pydantic schemas in query-api/schema/__init__.py
// and llm-gateway/app.py

// ─── Search ───────────────────────────────────────────────────────────

export interface SearchQuery {
    query: string;
    tenant_id: string;
    top_k?: number;
}

export interface CitationInfo {
    doc_id: string;
    source: string;
    source_id: string;
    version: number;
    chunk_index: number;
    section_path: string;
    heading_path: string[];
}

export interface SearchResult {
    doc_id: string;
    source: string;
    source_id: string;
    version: number;
    chunk_index: number;
    score: number;
    text: string;
    section_path: string;
    heading_path: string[];
    citation: CitationInfo;
}

export interface SearchResponse {
    query: string;
    results: SearchResult[];
}

// Enhanced search (HyDE + decomposition)
export interface EnhancedSearchQuery {
    query: string;
    tenant_id?: string;
    top_k?: number;
    use_hyde?: boolean;
    use_decomposition?: boolean;
    use_cache?: boolean;
}

export interface EnhancedSearchResponse {
    query: string;
    results: SearchResult[];
    total: number;
    time_ms: number;
    cached: boolean;
    hyde_used: boolean;
    decomposition_used: boolean;
    hyde_answer?: string;
    sub_queries?: string[];
}

// ─── RAG ──────────────────────────────────────────────────────────────

export interface RAGQuery {
    query: string;
    tenant_id: string;
    top_k?: number;
    session_id?: string;
    temperature?: number;
}

export interface RAGCitation {
    doc_id: string;
    source: string;
    source_id: string;
    version: number;
    section_path: string;
    heading_path: string[];
}

export interface RAGResponse {
    query: string;
    answer: string;
    citations: RAGCitation[];
    confidence: number;
    model?: string;
    session_id?: string;
}

// ─── LLM Gateway ─────────────────────────────────────────────────────

export interface LLMModelsResponse {
    provider: string;
    model?: string;
    models?: string[];
    current?: string;
    capabilities: string[];
}

// ─── Compare Mode ─────────────────────────────────────────────────────

export interface ComparisonQuery {
    query: string;
    tenant_id: string;
    models: string[];
    top_k?: number;
    temperature?: number;
}

export interface ComparisonResult {
    model: string;
    answer: string;
    citations: RAGCitation[];
    confidence: number;
    response_time_ms: number;
}

export interface ComparisonResponse {
    query: string;
    results: ComparisonResult[];
    total_time_ms: number;
}

// ─── Prompt Templates (frontend-only, stored locally) ─────────────────

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
    tenant_id?: string;
    created_at: string;
    updated_at: string;
}

// ─── Playground Settings ──────────────────────────────────────────────

export interface PlaygroundSettings {
    default_tenant_id?: string;
    default_model?: string;
    default_temperature?: number;
    default_top_k?: number;
    auto_save_prompts?: boolean;
}
