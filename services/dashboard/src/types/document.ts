export enum DocumentStatus {
    PENDING = 'pending',
    PROCESSING = 'processing',
    COMPLETED = 'completed',
    FAILED = 'failed',
    ARCHIVED = 'archived',
}

export interface Document {
    id: string;
    kb_id: string;
    name: string;
    status: DocumentStatus;
    size: number; // bytes
    chunk_count: number;
    version: number;
    content_type: string;
    source: string;
    source_id: string;
    metadata: Record<string, unknown>;
    is_latest: boolean;
    is_archived: boolean;
    created_at: string;
    updated_at: string | null;
}

export interface DocumentVersion {
    id: string;
    document_id: string;
    version: number;
    size: number;
    chunk_count: number;
    uploaded_by: string;
    created_at: string;
    change_summary?: string;
}

export interface DocumentUploadRequest {
    kb_id: string;
    files: File[];
    source?: string;
    metadata?: Record<string, unknown>;
}

export interface DocumentUploadProgress {
    file: File;
    progress: number; // 0-100
    status: 'pending' | 'uploading' | 'completed' | 'failed';
    error?: string;
    documentId?: string;
}
