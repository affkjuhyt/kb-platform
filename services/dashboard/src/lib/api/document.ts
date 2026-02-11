import { Document, DocumentVersion, DocumentUploadProgress, DocumentStatus } from '@/types/document';

// TODO: Replace mock data with actual API calls before production deployment
// When implementing real API integration:
// 1. Uncomment axios import and configure BASE_PATH
// 2. Replace Promise-based mock returns with actual axios calls
// 3. Implement proper file upload with FormData and progress tracking

// import axios from 'axios';
// const BASE_PATH = '/api/documents';

// Mock data for development
const MOCK_DOCUMENTS: Document[] = [
    {
        id: 'doc-1',
        kb_id: 'kb-1',
        name: 'API_Documentation.pdf',
        status: DocumentStatus.COMPLETED,
        size: 2457600, // ~2.4 MB
        chunk_count: 45,
        version: 2,
        content_type: 'application/pdf',
        source: 'upload',
        source_id: 'API_Documentation.pdf',
        metadata: { filename: 'API_Documentation.pdf' },
        is_latest: true,
        is_archived: false,
        created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
        updated_at: new Date(Date.now() - 86400000 * 1).toISOString(),
    },
    {
        id: 'doc-2',
        kb_id: 'kb-1',
        name: 'Getting_Started.md',
        status: DocumentStatus.COMPLETED,
        size: 15360, // ~15 KB
        chunk_count: 8,
        version: 1,
        content_type: 'text/markdown',
        source: 'upload',
        source_id: 'Getting_Started.md',
        metadata: { filename: 'Getting_Started.md' },
        is_latest: true,
        is_archived: false,
        created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
        updated_at: null,
    },
    {
        id: 'doc-3',
        kb_id: 'kb-1',
        name: 'troubleshooting.txt',
        status: DocumentStatus.PROCESSING,
        size: 8192, // ~8 KB
        chunk_count: 0,
        version: 1,
        content_type: 'text/plain',
        source: 'upload',
        source_id: 'troubleshooting.txt',
        metadata: { filename: 'troubleshooting.txt' },
        is_latest: true,
        is_archived: false,
        created_at: new Date(Date.now() - 3600000).toISOString(),
        updated_at: null,
    },
];

const MOCK_VERSIONS: Record<string, DocumentVersion[]> = {
    'doc-1': [
        {
            id: 'ver-1',
            document_id: 'doc-1',
            version: 2,
            size: 2457600,
            chunk_count: 45,
            uploaded_by: 'admin@example.com',
            created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
            change_summary: 'Updated API endpoints section',
        },
        {
            id: 'ver-2',
            document_id: 'doc-1',
            version: 1,
            size: 2400000,
            chunk_count: 42,
            uploaded_by: 'admin@example.com',
            created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
            change_summary: 'Initial upload',
        },
    ],
};

export const documentApi = {
    /**
     * List all documents for a knowledge base
     */
    list: async (kbId: string): Promise<Document[]> => {
        // TODO: Replace with actual API call
        // return axios.get(`${BASE_PATH}?kb_id=${kbId}`).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 300));
        return MOCK_DOCUMENTS.filter(doc => doc.kb_id === kbId && !doc.is_archived);
    },

    /**
     * Get a single document by ID
     */
    get: async (docId: string): Promise<Document> => {
        // TODO: Replace with actual API call
        // return axios.get(`${BASE_PATH}/${docId}`).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 200));
        const doc = MOCK_DOCUMENTS.find(d => d.id === docId);
        if (!doc) throw new Error('Document not found');
        return doc;
    },

    /**
     * Upload files to a knowledge base
     * Returns a function to track progress
     */
    upload: async (
        kbId: string,
        files: File[],
        source: string = 'upload',
        metadata: Record<string, unknown> = {},
        onProgress?: (progress: DocumentUploadProgress[]) => void
    ): Promise<Document[]> => {
        // TODO: Replace with actual API call using FormData
        // const formData = new FormData();
        // files.forEach(file => formData.append('files', file));
        // formData.append('kb_id', kbId);
        // formData.append('source', source);
        // formData.append('metadata', JSON.stringify(metadata));
        // 
        // return axios.post(`${BASE_PATH}/upload`, formData, {
        //     onUploadProgress: (progressEvent) => {
        //         // Calculate and report progress
        //     }
        // }).then(res => res.data);

        // Mock upload with simulated progress
        const progressStates: DocumentUploadProgress[] = files.map(file => ({
            file,
            progress: 0,
            status: 'pending',
        }));

        if (onProgress) onProgress([...progressStates]);

        const uploadedDocs: Document[] = [];

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            progressStates[i].status = 'uploading';

            // Simulate upload progress
            for (let p = 0; p <= 100; p += 20) {
                await new Promise(resolve => setTimeout(resolve, 100));
                progressStates[i].progress = p;
                if (onProgress) onProgress([...progressStates]);
            }

            // Create mock document
            const newDoc: Document = {
                id: `doc-${crypto.randomUUID()}`,
                kb_id: kbId,
                name: file.name,
                status: DocumentStatus.PROCESSING,
                size: file.size,
                chunk_count: 0,
                version: 1,
                content_type: file.type || 'application/octet-stream',
                source,
                source_id: file.name,
                metadata: { ...metadata, filename: file.name },
                is_latest: true,
                is_archived: false,
                created_at: new Date().toISOString(),
                updated_at: null,
            };

            MOCK_DOCUMENTS.push(newDoc);
            uploadedDocs.push(newDoc);

            progressStates[i].status = 'completed';
            progressStates[i].documentId = newDoc.id;
            if (onProgress) onProgress([...progressStates]);
        }

        return uploadedDocs;
    },

    /**
     * Get version history for a document
     */
    getVersions: async (docId: string): Promise<DocumentVersion[]> => {
        // TODO: Replace with actual API call
        // return axios.get(`${BASE_PATH}/${docId}/versions`).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 200));
        return MOCK_VERSIONS[docId] || [];
    },

    /**
     * Rollback to a previous version
     */
    rollback: async (docId: string, _versionId: string): Promise<Document> => {
        // TODO: Replace with actual API call
        // return axios.post(`${BASE_PATH}/${docId}/rollback`, { version_id: versionId }).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 500));
        const doc = MOCK_DOCUMENTS.find(d => d.id === docId);
        if (!doc) throw new Error('Document not found');

        // Simulate rollback by incrementing version
        doc.version += 1;
        doc.updated_at = new Date().toISOString();
        return doc;
    },

    /**
     * Delete a document (soft or hard delete)
     */
    delete: async (docId: string, hard: boolean = false): Promise<void> => {
        // TODO: Replace with actual API call
        // return axios.delete(`${BASE_PATH}/${docId}?hard=${hard}`);

        await new Promise(resolve => setTimeout(resolve, 300));
        const index = MOCK_DOCUMENTS.findIndex(d => d.id === docId);
        if (index !== -1) {
            if (hard) {
                MOCK_DOCUMENTS.splice(index, 1);
            } else {
                // Soft delete - just mark as archived
                MOCK_DOCUMENTS[index].is_archived = true;
                MOCK_DOCUMENTS[index].updated_at = new Date().toISOString();
            }
        }
    },

    /**
     * Archive a document
     */
    archive: async (docId: string): Promise<Document> => {
        // TODO: Replace with actual API call
        // return axios.post(`${BASE_PATH}/${docId}/archive`).then(res => res.data);

        await new Promise(resolve => setTimeout(resolve, 300));
        const doc = MOCK_DOCUMENTS.find(d => d.id === docId);
        if (!doc) throw new Error('Document not found');

        doc.is_archived = true;
        doc.updated_at = new Date().toISOString();
        return doc;
    },
};
