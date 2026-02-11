import apiClient, { getTenantId } from './client';
import {
    SearchQuery,
    SearchResponse,
    EnhancedSearchQuery,
    EnhancedSearchResponse,
    RAGQuery,
    RAGResponse,
    ComparisonQuery,
    ComparisonResponse,
    ComparisonResult,
    PromptTemplate,
    SavedPrompt,
    LLMModelsResponse,
} from '@/types/playground';

// ─── Local Storage Keys for Prompts ───────────────────────────────────

const PROMPTS_STORAGE_KEY = 'playground_saved_prompts';

// ─── Built-in Templates ──────────────────────────────────────────────

const BUILTIN_TEMPLATES: PromptTemplate[] = [
    {
        id: 'tpl-1',
        name: 'General Q&A',
        description: 'Standard question answering prompt',
        category: 'general',
        content: 'You are a helpful assistant. Answer the following question based on the provided context:\n\nContext: {context}\n\nQuestion: {question}',
        variables: ['context', 'question'],
        created_at: new Date().toISOString(),
    },
    {
        id: 'tpl-2',
        name: 'Technical Documentation',
        description: 'Prompt for technical documentation queries',
        category: 'technical',
        content: 'You are a technical documentation expert. Provide a clear, accurate answer with code examples when relevant.\n\nContext: {context}\n\nQuestion: {question}',
        variables: ['context', 'question'],
        created_at: new Date().toISOString(),
    },
    {
        id: 'tpl-3',
        name: 'Analytical Summary',
        description: 'Generate analytical summaries',
        category: 'analytical',
        content: 'Analyze the following information and provide a structured summary with key insights.\n\nContext: {context}\n\nFocus: {question}',
        variables: ['context', 'question'],
        created_at: new Date().toISOString(),
    },
];

// ─── Playground API ──────────────────────────────────────────────────

export const playgroundApi = {
    /**
     * Execute a search query via Query API
     * POST /query/search
     */
    search: async (query: SearchQuery): Promise<SearchResponse> => {
        const payload = {
            query: query.query,
            tenant_id: query.tenant_id || getTenantId(),
            top_k: query.top_k || 10,
        };
        const response = await apiClient.post<SearchResponse>('/query/search', payload);
        return response.data;
    },

    /**
     * Execute an enhanced search with HyDE and query decomposition
     * POST /query/search/enhanced
     */
    enhancedSearch: async (query: EnhancedSearchQuery): Promise<EnhancedSearchResponse> => {
        const payload = {
            query: query.query,
            tenant_id: query.tenant_id || getTenantId(),
            top_k: query.top_k || 10,
            use_hyde: query.use_hyde ?? false,
            use_decomposition: query.use_decomposition ?? false,
            use_cache: query.use_cache ?? true,
        };
        const response = await apiClient.post<EnhancedSearchResponse>('/query/search/enhanced', payload);
        return response.data;
    },

    /**
     * Execute a RAG query via Query API
     * POST /query/rag
     */
    rag: async (query: RAGQuery): Promise<RAGResponse> => {
        const payload = {
            query: query.query,
            tenant_id: query.tenant_id || getTenantId(),
            top_k: query.top_k || 5,
            temperature: query.temperature ?? 0.3,
            session_id: query.session_id,
        };
        const response = await apiClient.post<RAGResponse>('/query/rag', payload);
        return response.data;
    },


    /**
     * Streaming RAG via fetch API for SSE support
     */
    ragStreamFetch: async function* (
        query: string,
        context: string,
        options?: { temperature?: number; max_tokens?: number }
    ): AsyncGenerator<string, void, unknown> {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

        const response = await fetch('/api/llm/rag/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({
                query,
                context,
                max_tokens: options?.max_tokens || 1024,
                temperature: options?.temperature || 0.3,
            }),
        });

        if (!response.ok) {
            throw new Error(`Stream request failed: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') return;
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.chunk) {
                            yield parsed.chunk;
                        }
                    } catch {
                        // Skip malformed SSE lines
                    }
                }
            }
        }
    },

    /**
     * Execute comparison across multiple RAG calls
     * Sends parallel requests for each model configuration
     */
    compare: async (query: ComparisonQuery): Promise<ComparisonResponse> => {
        const startTime = Date.now();

        const results = await Promise.all(
            query.models.map(async (model): Promise<ComparisonResult> => {
                const modelStart = Date.now();
                try {
                    const ragResponse = await apiClient.post<RAGResponse>('/query/rag', {
                        query: query.query,
                        tenant_id: query.tenant_id || getTenantId(),
                        top_k: query.top_k || 5,
                        temperature: query.temperature ?? 0.3,
                    });

                    return {
                        model,
                        answer: ragResponse.data.answer,
                        citations: ragResponse.data.citations,
                        confidence: ragResponse.data.confidence,
                        response_time_ms: Date.now() - modelStart,
                    };
                } catch (_error) {
                    return {
                        model,
                        answer: `Error: Failed to get response from ${model}`,
                        citations: [],
                        confidence: 0,
                        response_time_ms: Date.now() - modelStart,
                    };
                }
            })
        );

        return {
            query: query.query,
            results,
            total_time_ms: Date.now() - startTime,
        };
    },

    /**
     * Get available LLM models
     * GET /llm/models
     */
    getModels: async (): Promise<LLMModelsResponse> => {
        const response = await apiClient.get<LLMModelsResponse>('/llm/models');
        return response.data;
    },

    /**
     * Get built-in prompt templates
     */
    getTemplates: async (): Promise<PromptTemplate[]> => {
        return BUILTIN_TEMPLATES;
    },

    /**
     * Save a custom prompt to localStorage
     */
    savePrompt: async (prompt: Omit<SavedPrompt, 'id' | 'created_at' | 'updated_at'>): Promise<SavedPrompt> => {
        const saved: SavedPrompt = {
            id: `prompt-${crypto.randomUUID()}`,
            ...prompt,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };

        const existing = playgroundApi.getSavedPromptsSync();
        existing.push(saved);

        if (typeof window !== 'undefined') {
            localStorage.setItem(PROMPTS_STORAGE_KEY, JSON.stringify(existing));
        }

        return saved;
    },

    /**
     * Get saved prompts from localStorage
     */
    getSavedPrompts: async (tenantId?: string): Promise<SavedPrompt[]> => {
        return playgroundApi.getSavedPromptsSync(tenantId);
    },

    /**
     * Sync helper for saved prompts
     */
    getSavedPromptsSync: (tenantId?: string): SavedPrompt[] => {
        if (typeof window === 'undefined') return [];

        try {
            const raw = localStorage.getItem(PROMPTS_STORAGE_KEY);
            if (!raw) return [];
            const prompts: SavedPrompt[] = JSON.parse(raw);
            if (tenantId) {
                return prompts.filter(p => !p.tenant_id || p.tenant_id === tenantId);
            }
            return prompts;
        } catch {
            return [];
        }
    },

    /**
     * Delete a saved prompt from localStorage
     */
    deletePrompt: async (promptId: string): Promise<void> => {
        if (typeof window === 'undefined') return;
        const existing = playgroundApi.getSavedPromptsSync();
        const filtered = existing.filter(p => p.id !== promptId);
        localStorage.setItem(PROMPTS_STORAGE_KEY, JSON.stringify(filtered));
    },
};
