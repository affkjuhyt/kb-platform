import apiClient, { getTenantId } from './client';
import { Document, DocumentVersion, DocumentUploadProgress, DocumentStatus } from '@/types/document';

/**
 * Document API client.
 *
 * Upload → POST /query/upload (proxied to Ingestion service)
 * List chunks → GET /query/chunks/source/{tenant_id}/{source}/{source_id}
 * Get text → GET /query/chunks/source/{tenant_id}/{source}/{source_id}/text
 */
export const documentApi = {
    /**
     * List all documents for a knowledge base (tenant)
     * GET /query/chunks/source/{tenant_id}/{source}/{source_id}
     * 
     * Note: The backend doesn't have a direct "list documents" endpoint.
     * We use the chunks endpoint grouped by source.
     * This may need a dedicated backend endpoint for production.
     */
    list: async (kbId: string): Promise<Document[]> => {
        try {
            // Try to get document list from the backend
            const response = await apiClient.get(`/query/chunks/source/${kbId}/upload`);
            return (response.data.documents || response.data || []).map((doc: Record<string, unknown>) => ({
                id: doc.id || doc.doc_id || crypto.randomUUID(),
                kb_id: kbId,
                name: doc.name || doc.source_id || 'Unknown',
                status: doc.status || DocumentStatus.COMPLETED,
                size: doc.size || 0,
                chunk_count: doc.chunk_count || 0,
                version: doc.version || 1,
                content_type: doc.content_type || 'application/octet-stream',
                source: (doc.source as string) || 'upload',
                source_id: (doc.source_id as string) || '',
                metadata: (doc.metadata as Record<string, unknown>) || {},
                is_latest: true,
                is_archived: false,
                created_at: (doc.created_at as string) || new Date().toISOString(),
                updated_at: (doc.updated_at as string) || null,
            }));
        } catch (error) {
            console.error('Failed to list documents:', error);
            return [];
        }
    },

    /**
     * Get a single document by ID
     */
    get: async (docId: string): Promise<Document> => {
        const tenantId = getTenantId() || 'default';
        const response = await apiClient.get(`/query/chunks/source/${tenantId}/upload/${docId}`);
        const doc = response.data;
        return {
            id: doc.id || doc.doc_id || docId,
            kb_id: tenantId,
            name: doc.name || doc.source_id || 'Unknown',
            status: doc.status || DocumentStatus.COMPLETED,
            size: doc.size || 0,
            chunk_count: doc.chunk_count || 0,
            version: doc.version || 1,
            content_type: doc.content_type || 'application/octet-stream',
            source: doc.source || 'upload',
            source_id: doc.source_id || '',
            metadata: doc.metadata || {},
            is_latest: true,
            is_archived: false,
            created_at: doc.created_at || new Date().toISOString(),
            updated_at: doc.updated_at || null,
        };
    },

    /**
     * Upload files to a knowledge base via Ingestion service
     * POST /query/upload (proxied through API Gateway → Ingestion)
     */
    upload: async (
        kbId: string,
        files: File[],
        source: string = 'upload',
        metadata: Record<string, unknown> = {},
        onProgress?: (progress: DocumentUploadProgress[]) => void
    ): Promise<Document[]> => {
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
            if (onProgress) onProgress([...progressStates]);

            try {
                const formData = new FormData();
                formData.append('files', file);
                formData.append('tenant_id', kbId);
                formData.append('source', source);
                if (Object.keys(metadata).length > 0) {
                    formData.append('metadata', JSON.stringify(metadata));
                }

                const response = await apiClient.post('/query/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                    onUploadProgress: (progressEvent) => {
                        const total = progressEvent.total || file.size;
                        const percent = Math.round((progressEvent.loaded / total) * 100);
                        progressStates[i].progress = percent;
                        if (onProgress) onProgress([...progressStates]);
                    },
                });

                const docData = response.data;
                const newDoc: Document = {
                    id: docData.id || docData.doc_id || crypto.randomUUID(),
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

                uploadedDocs.push(newDoc);
                progressStates[i].status = 'completed';
                progressStates[i].progress = 100;
                progressStates[i].documentId = newDoc.id;
            } catch (error) {
                progressStates[i].status = 'failed';
                progressStates[i].error = error instanceof Error ? error.message : 'Upload failed';
            }

            if (onProgress) onProgress([...progressStates]);
        }

        return uploadedDocs;
    },

    /**
     * Get version history for a document
     * Note: Backend may not support versioning yet — returns empty array as fallback
     */
    getVersions: async (docId: string): Promise<DocumentVersion[]> => {
        try {
            const response = await apiClient.get(`/query/documents/${docId}/versions`);
            return response.data;
        } catch {
            // Versioning endpoint may not exist yet
            return [];
        }
    },

    /**
     * Delete a document
     */
    delete: async (docId: string, _hard: boolean = false): Promise<void> => {
        const tenantId = getTenantId() || 'default';
        await apiClient.delete(`/query/documents/${docId}`, {
            params: { tenant_id: tenantId },
        });
    },

    /**
     * Get document content/text for preview
     * GET /query/chunks/source/{tenant_id}/{source}/{source_id}/text
     */
    getContent: async (docId: string): Promise<string> => {
        const tenantId = getTenantId() || 'default';
        try {
            const response = await apiClient.get(
                `/query/chunks/source/${tenantId}/upload/${docId}/text`
            );
            return response.data.text || response.data;
        } catch {
            return 'Document content preview is not available.';
        }
    },
};
