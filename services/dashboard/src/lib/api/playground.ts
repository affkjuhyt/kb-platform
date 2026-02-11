import {
    SearchQuery,
    SearchResponse,
    RAGQuery,
    RAGResponse,
    ComparisonQuery,
    ComparisonResponse,
    PromptTemplate,
    SavedPrompt,
    SearchResult,
    Citation,
} from '@/types/playground';

// TODO: Replace mock data with actual API calls before production deployment
// When implementing real API integration:
// 1. Uncomment axios import and configure BASE_PATH
// 2. Replace Promise-based mock returns with actual axios calls
// 3. Implement proper error handling and response validation

// import axios from 'axios';
// const BASE_PATH = '/api/playground';

// Mock data for development
const MOCK_SEARCH_RESULTS: SearchResult[] = [
    {
        id: 'chunk-1',
        content: 'Knowledge bases are structured repositories of information that enable efficient retrieval and question answering. They typically use vector embeddings to represent semantic meaning.',
        score: 0.92,
        metadata: {
            document_id: 'doc-1',
            document_name: 'Introduction to Knowledge Bases.pdf',
            chunk_index: 0,
            source: 'upload',
            created_at: new Date().toISOString(),
        },
        highlights: ['Knowledge bases', 'vector embeddings', 'semantic meaning'],
    },
    {
        id: 'chunk-2',
        content: 'Vector search uses cosine similarity or other distance metrics to find semantically similar content. This enables more intelligent search compared to keyword matching.',
        score: 0.87,
        metadata: {
            document_id: 'doc-2',
            document_name: 'Vector Search Guide.md',
            chunk_index: 5,
            source: 'web_crawler',
            created_at: new Date().toISOString(),
        },
        highlights: ['Vector search', 'cosine similarity', 'semantically similar'],
    },
];

const MOCK_CITATIONS: Citation[] = [
    {
        index: 1,
        document_id: 'doc-1',
        document_name: 'Introduction to Knowledge Bases.pdf',
        chunk_content: 'Knowledge bases are structured repositories of information...',
        score: 0.92,
    },
    {
        index: 2,
        document_id: 'doc-2',
        document_name: 'Vector Search Guide.md',
        chunk_content: 'Vector search uses cosine similarity...',
        score: 0.87,
    },
];

export const playgroundApi = {
    /**
     * Execute a search query
     */
    search: async (query: SearchQuery): Promise<SearchResponse> => {
        // TODO: Replace with actual API call
        // return axios.post(`${BASE_PATH}/search`, query).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 500));

        return {
            results: MOCK_SEARCH_RESULTS,
            total: MOCK_SEARCH_RESULTS.length,
            query_time_ms: 127,
        };
    },

    /**
     * Execute a RAG query
     */
    rag: async (query: RAGQuery): Promise<RAGResponse> => {
        // TODO: Replace with actual API call
        // return axios.post(`${BASE_PATH}/rag`, query).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 1500));

        return {
            answer: `Based on the knowledge base, ${query.query.toLowerCase()} can be explained as follows:\n\nKnowledge bases are structured repositories that use vector embeddings to represent semantic meaning [1]. This enables efficient retrieval through vector search, which uses cosine similarity to find semantically similar content [2]. This approach is more intelligent than traditional keyword matching.`,
            citations: MOCK_CITATIONS,
            model: query.model || 'gpt-4',
            tokens_used: 245,
            response_time_ms: 1423,
        };
    },

    /**
     * Execute comparison across multiple models
     */
    compare: async (query: ComparisonQuery): Promise<ComparisonResponse> => {
        // TODO: Replace with actual API call
        // return axios.post(`${BASE_PATH}/compare`, query).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 2000));

        const results = query.models.map((model, idx) => ({
            model,
            answer: `[${model}] Based on the knowledge base, ${query.query.toLowerCase()} involves using vector embeddings and semantic search. ${idx === 0 ? 'This is a more detailed explanation with additional context.' : 'This is a concise summary.'}`,
            citations: MOCK_CITATIONS,
            tokens_used: 200 + idx * 50,
            response_time_ms: 1200 + idx * 300,
        }));

        return {
            query: query.query,
            results,
            total_time_ms: 2000,
        };
    },

    /**
     * Get available prompt templates
     */
    getTemplates: async (): Promise<PromptTemplate[]> => {
        // TODO: Replace with actual API call
        // return axios.get(`${BASE_PATH}/templates`).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 200));

        return [
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
    },

    /**
     * Save a custom prompt
     */
    savePrompt: async (prompt: Omit<SavedPrompt, 'id' | 'created_at' | 'updated_at'>): Promise<SavedPrompt> => {
        // TODO: Replace with actual API call
        // return axios.post(`${BASE_PATH}/prompts`, prompt).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 300));

        return {
            id: `prompt-${crypto.randomUUID()}`,
            ...prompt,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };
    },

    /**
     * Get saved prompts
     */
    getSavedPrompts: async (kbId?: string): Promise<SavedPrompt[]> => {
        // TODO: Replace with actual API call
        // return axios.get(`${BASE_PATH}/prompts`, { params: { kb_id: kbId } }).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 200));

        return [
            {
                id: 'saved-1',
                name: 'My Custom Prompt',
                content: 'Custom prompt content here...',
                kb_id: kbId,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
            },
        ];
    },
};
