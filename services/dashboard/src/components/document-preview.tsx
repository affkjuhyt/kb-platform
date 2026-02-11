"use client"

import { useState, useEffect, useCallback } from "react"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, FileText, Clock, Info, History } from "lucide-react"
import { Document, DocumentVersion } from "@/types/document"
import { documentApi } from "@/lib/api/document"
import { formatDate, DATE_FORMATS } from "@/lib/utils/date"
import { formatFileSize } from "@/lib/utils/format"

interface DocumentPreviewProps {
    document: Document | null
    open: boolean
    onOpenChange: (open: boolean) => void
}

export function DocumentPreview({ document, open, onOpenChange }: DocumentPreviewProps) {
    const [content, setContent] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [versions, setVersions] = useState<DocumentVersion[]>([])
    const [isLoadingVersions, setIsLoadingVersions] = useState(false)

    const loadContent = useCallback(async () => {
        if (!document) return
        try {
            setIsLoading(true)
            const data = await documentApi.getContent(document.id)
            setContent(data)
        } catch (error) {
            console.error("Failed to load document content:", error)
            setContent("Error loading content.")
        } finally {
            setIsLoading(false)
        }
    }, [document])

    const loadVersions = useCallback(async () => {
        if (!document) return
        try {
            setIsLoadingVersions(true)
            const data = await documentApi.getVersions(document.id)
            setVersions(data)
        } catch (error) {
            console.error("Failed to load versions:", error)
        } finally {
            setIsLoadingVersions(false)
        }
    }, [document])

    useEffect(() => {
        if (open && document) {
            loadContent()
            loadVersions()
        } else {
            setContent(null)
            setVersions([])
        }
    }, [open, document, loadContent, loadVersions])

    if (!document) return null

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[800px] h-[80vh] flex flex-col p-0 overflow-hidden">
                <DialogHeader className="p-6 pb-0">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <FileText className="h-6 w-6 text-primary" />
                            <div>
                                <DialogTitle className="text-xl">{document.name}</DialogTitle>
                                <DialogDescription className="text-xs">
                                    ID: {document.id} | Size: {formatFileSize(document.size)}
                                </DialogDescription>
                            </div>
                        </div>
                        <Badge variant={document.status === 'completed' ? 'outline' : 'secondary'}>
                            {document.status}
                        </Badge>
                    </div>
                </DialogHeader>

                <Tabs defaultValue="content" className="flex-1 flex flex-col mt-4">
                    <div className="px-6">
                        <TabsList className="grid w-full grid-cols-3">
                            <TabsTrigger value="content">
                                <FileText className="h-4 w-4 mr-2" /> Content
                            </TabsTrigger>
                            <TabsTrigger value="metadata">
                                <Info className="h-4 w-4 mr-2" /> Details
                            </TabsTrigger>
                            <TabsTrigger value="versions">
                                <History className="h-4 w-4 mr-2" /> History
                            </TabsTrigger>
                        </TabsList>
                    </div>

                    <TabsContent value="content" className="flex-1 mt-0 overflow-hidden">
                        <ScrollArea className="h-full p-6 bg-muted/30">
                            {isLoading ? (
                                <div className="flex items-center justify-center h-full">
                                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                                </div>
                            ) : content ? (
                                <div className="prose prose-sm dark:prose-invert max-w-none">
                                    {/* Simple Markdown-like rendering for mock */}
                                    {content.split('\n').map((line, i) => {
                                        if (line.startsWith('# ')) return <h1 key={i}>{line.substring(2)}</h1>
                                        if (line.startsWith('## ')) return <h2 key={i}>{line.substring(3)}</h2>
                                        if (!line.trim()) return <br key={i} />
                                        return <p key={i}>{line}</p>
                                    })}
                                </div>
                            ) : (
                                <p className="text-center text-muted-foreground">No content available.</p>
                            )}
                        </ScrollArea>
                    </TabsContent>

                    <TabsContent value="metadata" className="flex-1 mt-0 overflow-hidden">
                        <ScrollArea className="h-full p-6">
                            <div className="space-y-6">
                                <div>
                                    <h3 className="text-sm font-semibold mb-3 flex items-center">
                                        <Info className="h-4 w-4 mr-2" /> General Information
                                    </h3>
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div className="space-y-1">
                                            <p className="text-muted-foreground">Source</p>
                                            <p className="font-medium capitalize">{document.source}</p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-muted-foreground">Content Type</p>
                                            <p className="font-medium">{document.content_type}</p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-muted-foreground">Chunks</p>
                                            <p className="font-medium">{document.chunk_count}</p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-muted-foreground">Current Version</p>
                                            <p className="font-medium">v{document.version}</p>
                                        </div>
                                    </div>
                                </div>

                                <div>
                                    <h3 className="text-sm font-semibold mb-3 flex items-center">
                                        <Clock className="h-4 w-4 mr-2" /> Timestamps
                                    </h3>
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div className="space-y-1">
                                            <p className="text-muted-foreground">Created At</p>
                                            <p className="font-medium">{formatDate(document.created_at, DATE_FORMATS.WITH_TIME)}</p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-muted-foreground">Last Updated</p>
                                            <p className="font-medium">
                                                {document.updated_at ? formatDate(document.updated_at, DATE_FORMATS.WITH_TIME) : 'Never'}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {document.metadata && Object.keys(document.metadata).length > 0 && (
                                    <div>
                                        <h3 className="text-sm font-semibold mb-3">Technical Metadata</h3>
                                        <pre className="text-xs bg-muted p-4 rounded-lg overflow-x-auto">
                                            {JSON.stringify(document.metadata, null, 2)}
                                        </pre>
                                    </div>
                                )}
                            </div>
                        </ScrollArea>
                    </TabsContent>

                    <TabsContent value="versions" className="flex-1 mt-0 overflow-hidden">
                        <ScrollArea className="h-full p-6">
                            {isLoadingVersions ? (
                                <div className="flex items-center justify-center h-full">
                                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                                </div>
                            ) : versions.length > 0 ? (
                                <div className="space-y-4">
                                    {versions.map((ver) => (
                                        <div key={ver.id} className="flex items-start justify-between p-4 border rounded-lg bg-muted/10">
                                            <div>
                                                <p className="font-semibold">Version {ver.version}</p>
                                                <p className="text-xs text-muted-foreground mb-2">
                                                    Uploaded by {ver.uploaded_by} on {formatDate(ver.created_at, DATE_FORMATS.WITH_TIME)}
                                                </p>
                                                {ver.change_summary && (
                                                    <p className="text-sm italic text-muted-foreground">
                                                        &quot;{ver.change_summary}&quot;
                                                    </p>
                                                )}
                                            </div>
                                            {ver.version === document.version ? (
                                                <Badge>Current</Badge>
                                            ) : (
                                                <Button variant="outline" size="sm">
                                                    Rollback
                                                </Button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-center text-muted-foreground">No version history found.</p>
                            )}
                        </ScrollArea>
                    </TabsContent>
                </Tabs>
            </DialogContent>
        </Dialog>
    )
}

function Button({ className, children, ...props }: React.ComponentProps<"button"> & { variant?: string, size?: string }) {
    // Basic shim if not already available in parent components
    return (
        <button
            className={`inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground h-9 px-4 py-2 ${className}`}
            {...props}
        >
            {children}
        </button>
    )
}
