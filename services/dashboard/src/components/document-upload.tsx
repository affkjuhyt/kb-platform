"use client"

import { useState, useCallback, useRef } from "react"
import { Upload, X, FileText, Loader2, CheckCircle2, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Progress } from "@/components/ui/progress"
import { documentApi } from "@/lib/api/document"
import { DocumentUploadProgress } from "@/types/document"
import { toast } from "sonner"

interface DocumentUploadProps {
    kbId: string
    open: boolean
    onOpenChange: (open: boolean) => void
    onUploadComplete: () => void
}

export function DocumentUpload({ kbId, open, onOpenChange, onUploadComplete }: DocumentUploadProps) {
    const [files, setFiles] = useState<File[]>([])
    const [uploadProgress, setUploadProgress] = useState<DocumentUploadProgress[]>([])
    const [isUploading, setIsUploading] = useState(false)
    const [isDragging, setIsDragging] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(true)
    }, [])

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(false)
    }, [])

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(false)

        const droppedFiles = Array.from(e.dataTransfer.files)
        setFiles(prev => [...prev, ...droppedFiles])
    }, [])

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const selectedFiles = Array.from(e.target.files)
            setFiles(prev => [...prev, ...selectedFiles])
        }
    }, [])

    const removeFile = useCallback((index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index))
    }, [])

    const handleUpload = async () => {
        if (files.length === 0) return

        setIsUploading(true)

        try {
            await documentApi.upload(
                kbId,
                files,
                'upload',
                {},
                (progress) => {
                    setUploadProgress(progress)
                }
            )

            toast.success(`Successfully uploaded ${files.length} document${files.length > 1 ? 's' : ''}`)
            onUploadComplete()
            handleClose()
        } catch (error) {
            console.error(error)
            toast.error("Failed to upload documents")
        } finally {
            setIsUploading(false)
        }
    }

    const handleClose = () => {
        if (!isUploading) {
            setFiles([])
            setUploadProgress([])
            onOpenChange(false)
        }
    }

    const formatFileSize = (bytes: number): string => {
        if (bytes === 0) return '0 B'
        const k = 1024
        const sizes = ['B', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
    }

    const getProgressForFile = (file: File) => {
        return uploadProgress.find(p => p.file === file)
    }

    const getStatusIcon = (status: 'pending' | 'uploading' | 'completed' | 'failed') => {
        switch (status) {
            case 'completed':
                return <CheckCircle2 className="h-4 w-4 text-green-500" />
            case 'failed':
                return <AlertCircle className="h-4 w-4 text-destructive" />
            case 'uploading':
                return <Loader2 className="h-4 w-4 animate-spin text-primary" />
            default:
                return <FileText className="h-4 w-4 text-muted-foreground" />
        }
    }

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>Upload Documents</DialogTitle>
                    <DialogDescription>
                        Upload files to be indexed in this knowledge base. Supported formats: PDF, DOCX, TXT, MD, HTML.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    {/* Drag and Drop Zone */}
                    <div
                        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${isDragging
                                ? 'border-primary bg-primary/5'
                                : 'border-muted-foreground/25 hover:border-muted-foreground/50'
                            }`}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
                        <p className="text-sm font-medium mb-1">
                            Drag and drop files here, or click to browse
                        </p>
                        <p className="text-xs text-muted-foreground">
                            Maximum file size: 50MB per file
                        </p>
                        <input
                            ref={fileInputRef}
                            type="file"
                            multiple
                            className="hidden"
                            onChange={handleFileSelect}
                            accept=".pdf,.docx,.txt,.md,.html,.htm"
                        />
                    </div>

                    {/* File List */}
                    {files.length > 0 && (
                        <div className="space-y-2 max-h-[300px] overflow-y-auto">
                            <p className="text-sm font-medium">
                                {files.length} file{files.length > 1 ? 's' : ''} selected
                            </p>
                            {files.map((file, index) => {
                                const progress = getProgressForFile(file)
                                return (
                                    <div
                                        key={`${file.name}-${index}`}
                                        className="flex items-center gap-3 p-3 border rounded-lg"
                                    >
                                        {progress ? getStatusIcon(progress.status) : <FileText className="h-4 w-4 text-muted-foreground" />}
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium truncate">{file.name}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {formatFileSize(file.size)}
                                            </p>
                                            {progress && progress.status === 'uploading' && (
                                                <Progress value={progress.progress} className="mt-2 h-1" />
                                            )}
                                            {progress && progress.status === 'failed' && progress.error && (
                                                <p className="text-xs text-destructive mt-1">{progress.error}</p>
                                            )}
                                        </div>
                                        {!isUploading && (
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-8 w-8 p-0"
                                                onClick={() => removeFile(index)}
                                            >
                                                <X className="h-4 w-4" />
                                            </Button>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={handleClose} disabled={isUploading}>
                        Cancel
                    </Button>
                    <Button onClick={handleUpload} disabled={files.length === 0 || isUploading}>
                        {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Upload {files.length > 0 && `(${files.length})`}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
