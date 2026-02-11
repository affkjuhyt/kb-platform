"use client"

import { useEffect, useState, useCallback, useMemo } from "react"
import { useParams, useRouter } from "next/navigation"
import { KnowledgeBase } from "@/types/knowledge-base"
import { Document, DocumentStatus } from "@/types/document"
import { kbApi } from "@/lib/api/knowledge-base"
import { documentApi } from "@/lib/api/document"
import {
    Loader2,
    ArrowLeft,
    Database,
    FileText,
    BarChart3,
    Settings as SettingsIcon,
    AlertCircle,
    Upload,
    Search,
    Trash2,
    Archive,
    Eye,
    MoreHorizontal,
    Globe,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from "@/components/ui/tabs"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { KBAnalytics } from "@/components/kb-analytics"
import { formatDate, DATE_FORMATS } from "@/lib/utils/date"
import { formatFileSize } from "@/lib/utils/format"
import { DocumentUpload } from "@/components/document-upload"
import { DocumentPreview } from "@/components/document-preview"
import { DataSourcesList } from "@/components/data-sources-list"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"

export default function KBDetailPage() {
    const params = useParams()
    const router = useRouter()
    const kbId = params.kbId as string

    const [kb, setKb] = useState<KnowledgeBase | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false)
    const [isDeletingKB, setIsDeletingKB] = useState(false)

    // Document state
    const [documents, setDocuments] = useState<Document[]>([])
    const [isLoadingDocs, setIsLoadingDocs] = useState(false)
    const [docSearchQuery, setDocSearchQuery] = useState("")
    const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set())
    const [docToDelete, setDocToDelete] = useState<Document | null>(null)
    const [isDeleteDocOpen, setIsDeleteDocOpen] = useState(false)
    const [isDeletingDoc, setIsDeletingDoc] = useState(false)
    const [isUploadOpen, setIsUploadOpen] = useState(false)
    const [docForPreview, setDocForPreview] = useState<Document | null>(null)
    const [isPreviewOpen, setIsPreviewOpen] = useState(false)

    const loadKB = useCallback(async () => {
        try {
            setIsLoading(true)
            const data = await kbApi.get(kbId)
            setKb(data)
            setError(null)
        } catch (err: unknown) {
            console.error(err)
            setError("Knowledge base not found or an error occurred.")
            toast.error("Failed to load knowledge base")
        } finally {
            setIsLoading(false)
        }
    }, [kbId])

    useEffect(() => {
        if (kbId) {
            loadKB()
        }
    }, [kbId, loadKB])

    const handleDelete = async () => {
        try {
            setIsDeletingKB(true)
            await kbApi.delete(kbId)
            toast.success("Knowledge base deleted successfully")
            router.push("/dashboard/kb")
        } catch (err: unknown) {
            console.error(err)
            toast.error("Failed to delete knowledge base")
        } finally {
            setIsDeletingKB(false)
            setIsDeleteConfirmOpen(false)
        }
    }

    const loadDocuments = useCallback(async () => {
        if (!kbId) return

        try {
            setIsLoadingDocs(true)
            const docs = await documentApi.list(kbId)
            setDocuments(docs)
        } catch (err: unknown) {
            console.error(err)
            toast.error("Failed to load documents")
        } finally {
            setIsLoadingDocs(false)
        }
    }, [kbId])

    const handleDeleteDocument = async () => {
        if (!docToDelete) return

        try {
            setIsDeletingDoc(true)
            await documentApi.delete(docToDelete.id, false) // soft delete
            toast.success("Document deleted")
            setDocuments(prev => prev.filter(d => d.id !== docToDelete.id))

            // Remove from selection if deleted
            setSelectedDocs(prev => {
                const next = new Set(prev)
                next.delete(docToDelete.id)
                return next
            })

            setIsDeleteDocOpen(false)
            setDocToDelete(null)
        } catch (err: unknown) {
            console.error(err)
            toast.error("Failed to delete document")
        } finally {
            setIsDeletingDoc(false)
        }
    }

    const handleBulkDelete = async () => {
        if (selectedDocs.size === 0) return

        try {
            setIsLoadingDocs(true)
            // In mock mode, we just loop
            for (const docId of Array.from(selectedDocs)) {
                await documentApi.delete(docId, false)
            }
            toast.success(`Successfully deleted ${selectedDocs.size} documents`)
            setDocuments(prev => prev.filter(d => !selectedDocs.has(d.id)))
            setSelectedDocs(new Set())
        } catch (err) {
            console.error(err)
            toast.error("Failed to delete some documents")
        } finally {
            setIsLoadingDocs(false)
        }
    }

    const handleBulkArchive = async () => {
        if (selectedDocs.size === 0) return

        try {
            setIsLoadingDocs(true)
            for (const docId of Array.from(selectedDocs)) {
                await documentApi.archive(docId)
            }
            toast.success(`Successfully archived ${selectedDocs.size} documents`)
            setDocuments(prev => prev.filter(d => !selectedDocs.has(d.id)))
            setSelectedDocs(new Set())
        } catch (err) {
            console.error(err)
            toast.error("Failed to archive some documents")
        } finally {
            setIsLoadingDocs(false)
        }
    }

    const toggleDocSelection = (docId: string) => {
        setSelectedDocs(prev => {
            const next = new Set(prev)
            if (next.has(docId)) {
                next.delete(docId)
            } else {
                next.add(docId)
            }
            return next
        })
    }

    const toggleAllDocs = () => {
        if (selectedDocs.size === filteredDocs.length) {
            setSelectedDocs(new Set())
        } else {
            setSelectedDocs(new Set(filteredDocs.map((d: Document) => d.id)))
        }
    }

    const getStatusBadge = (status: DocumentStatus) => {
        const variants: Record<DocumentStatus, { variant: "default" | "secondary" | "destructive" | "outline", label: string }> = {
            [DocumentStatus.PENDING]: { variant: "secondary", label: "Pending" },
            [DocumentStatus.PROCESSING]: { variant: "default", label: "Processing" },
            [DocumentStatus.COMPLETED]: { variant: "outline", label: "Completed" },
            [DocumentStatus.FAILED]: { variant: "destructive", label: "Failed" },
            [DocumentStatus.ARCHIVED]: { variant: "secondary", label: "Archived" },
        }
        const config = variants[status]
        return <Badge variant={config.variant}>{config.label}</Badge>
    }

    const filteredDocs = useMemo(() =>
        documents.filter(doc =>
            doc.name.toLowerCase().includes(docSearchQuery.toLowerCase())
        ), [documents, docSearchQuery])

    useEffect(() => {
        if (kbId) {
            loadDocuments()
        }
    }, [kbId, loadDocuments])

    if (isLoading) {
        return (
            <div className="flex h-full items-center justify-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    if (error || !kb) {
        return (
            <div className="flex flex-col items-center justify-center h-full space-y-4 p-8">
                <AlertCircle className="h-12 w-12 text-destructive" />
                <h3 className="text-xl font-bold">Error</h3>
                <p className="text-muted-foreground">{error || "Something went wrong"}</p>
                <Button variant="outline" onClick={() => router.push("/dashboard/kb")}>
                    Back to Knowledge Bases
                </Button>
            </div>
        )
    }

    return (
        <div className="h-full flex-1 flex-col space-y-8 p-8 md:flex">
            <div className="flex items-center space-x-4">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => router.push("/dashboard/kb")}
                >
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <div className="flex items-center space-x-2">
                        <h2 className="text-2xl font-bold tracking-tight">{kb.name}</h2>
                        <Badge variant="outline">{kb.embedding_model}</Badge>
                    </div>
                    <p className="text-muted-foreground">
                        {kb.description || "No description provided."}
                    </p>
                </div>
            </div>

            <Tabs defaultValue="overview" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="overview">
                        <Database className="mr-2 h-4 w-4" /> Overview
                    </TabsTrigger>
                    <TabsTrigger value="documents">
                        <FileText className="mr-2 h-4 w-4" /> Documents
                    </TabsTrigger>
                    <TabsTrigger value="data-sources">
                        <Globe className="mr-2 h-4 w-4" /> Data Sources
                    </TabsTrigger>
                    <TabsTrigger value="analytics">
                        <BarChart3 className="mr-2 h-4 w-4" /> Analytics
                    </TabsTrigger>
                    <TabsTrigger value="settings">
                        <SettingsIcon className="mr-2 h-4 w-4" /> Settings
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
                                <FileText className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{kb.document_count}</div>
                                <p className="text-xs text-muted-foreground">
                                    Files indexed in this KB
                                </p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Total Chunks</CardTitle>
                                <Database className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{kb.chunk_count}</div>
                                <p className="text-xs text-muted-foreground">
                                    Vector shards generated
                                </p>
                            </CardContent>
                        </Card>
                    </div>

                    <Card>
                        <CardHeader>
                            <CardTitle>Configuration</CardTitle>
                            <CardDescription>Vector search and embedding parameters</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="font-semibold">Embedding Model:</span>
                                    <p className="text-muted-foreground">{kb.embedding_model}</p>
                                </div>
                                <div>
                                    <span className="font-semibold">Created At:</span>
                                    <p className="text-muted-foreground">
                                        {formatDate(kb.created_at, DATE_FORMATS.WITH_TIME)}
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="documents" className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="relative w-[300px]">
                            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Filter documents..."
                                value={docSearchQuery}
                                onChange={(e) => setDocSearchQuery(e.target.value)}
                                className="pl-8"
                            />
                        </div>
                        <Button onClick={() => setIsUploadOpen(true)}>
                            <Upload className="mr-2 h-4 w-4" /> Upload Documents
                        </Button>
                    </div>

                    <Card>
                        <CardHeader>
                            <CardTitle>Documents</CardTitle>
                            <CardDescription>
                                {documents.length} document{documents.length !== 1 ? 's' : ''} indexed in this knowledge base
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {isLoadingDocs ? (
                                <div className="flex items-center justify-center h-32">
                                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                                </div>
                            ) : filteredDocs.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-32 text-center">
                                    <FileText className="h-12 w-12 text-muted-foreground mb-2" />
                                    <p className="text-muted-foreground">
                                        {docSearchQuery ? "No matching documents found" : "No documents uploaded yet"}
                                    </p>
                                </div>
                            ) : (
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead className="w-[40px]">
                                                <Checkbox
                                                    checked={selectedDocs.size === filteredDocs.length && filteredDocs.length > 0}
                                                    onCheckedChange={toggleAllDocs}
                                                    aria-label="Select all"
                                                />
                                            </TableHead>
                                            <TableHead>Name</TableHead>
                                            <TableHead>Status</TableHead>
                                            <TableHead>Size</TableHead>
                                            <TableHead>Chunks</TableHead>
                                            <TableHead>Version</TableHead>
                                            <TableHead>Updated</TableHead>
                                            <TableHead className="w-[100px]">Actions</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {filteredDocs.map((doc: Document) => (
                                            <TableRow key={doc.id}>
                                                <TableCell>
                                                    <Checkbox
                                                        checked={selectedDocs.has(doc.id)}
                                                        onCheckedChange={() => toggleDocSelection(doc.id)}
                                                        aria-label={`Select ${doc.name}`}
                                                    />
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex items-center space-x-2">
                                                        <FileText className="h-4 w-4 text-muted-foreground" />
                                                        <span className="font-medium">{doc.name}</span>
                                                    </div>
                                                </TableCell>
                                                <TableCell>{getStatusBadge(doc.status)}</TableCell>
                                                <TableCell className="text-muted-foreground">
                                                    {formatFileSize(doc.size)}
                                                </TableCell>
                                                <TableCell className="text-muted-foreground">
                                                    {doc.chunk_count}
                                                </TableCell>
                                                <TableCell className="text-muted-foreground">
                                                    v{doc.version}
                                                </TableCell>
                                                <TableCell className="text-muted-foreground">
                                                    {formatDate(doc.updated_at || doc.created_at)}
                                                </TableCell>
                                                <TableCell>
                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger asChild>
                                                            <Button variant="ghost" className="h-8 w-8 p-0">
                                                                <span className="sr-only">Open menu</span>
                                                                <MoreHorizontal className="h-4 w-4" />
                                                            </Button>
                                                        </DropdownMenuTrigger>
                                                        <DropdownMenuContent align="end">
                                                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                                            <DropdownMenuItem onClick={() => {
                                                                setDocForPreview(doc)
                                                                setIsPreviewOpen(true)
                                                            }}>
                                                                <Eye className="mr-2 h-4 w-4" />
                                                                Preview
                                                            </DropdownMenuItem>
                                                            <DropdownMenuSeparator />
                                                            <DropdownMenuItem>
                                                                <Archive className="mr-2 h-4 w-4" />
                                                                Archive
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem
                                                                className="text-destructive focus:text-destructive"
                                                                onClick={() => {
                                                                    setDocToDelete(doc)
                                                                    setIsDeleteDocOpen(true)
                                                                }}
                                                            >
                                                                <Trash2 className="mr-2 h-4 w-4" />
                                                                Delete
                                                            </DropdownMenuItem>
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            )}
                        </CardContent>
                    </Card>

                    {/* Bulk Action Toolbar */}
                    {selectedDocs.size > 0 && (
                        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-popover border shadow-lg rounded-full px-6 py-3 flex items-center gap-6 animate-in slide-in-from-bottom-4 z-50">
                            <span className="text-sm font-medium">
                                {selectedDocs.size} item{selectedDocs.size !== 1 ? 's' : ''} selected
                            </span>
                            <Separator orientation="vertical" className="h-4" />
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleBulkArchive}
                                    className="h-8"
                                >
                                    <Archive className="h-4 w-4 mr-2" /> Archive
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleBulkDelete}
                                    className="h-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                                >
                                    <Trash2 className="h-4 w-4 mr-2" /> Delete
                                </Button>
                            </div>
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="data-sources">
                    <Card>
                        <CardHeader>
                            <CardTitle>Data Sources</CardTitle>
                            <CardDescription>Manage automated data ingestion from web crawlers, APIs, and file watchers.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <DataSourcesList kbId={kbId} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="analytics">
                    <KBAnalytics kbId={kbId} />
                </TabsContent>

                <TabsContent value="settings">
                    <Card>
                        <CardHeader>
                            <CardTitle>Danger Zone</CardTitle>
                            <CardDescription>Irreversible actions for this knowledge base.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center justify-between border-t pt-4">
                                <div>
                                    <p className="font-semibold">Delete Knowledge Base</p>
                                    <p className="text-sm text-muted-foreground">
                                        This will permanently delete the KB and all its indexed data.
                                    </p>
                                </div>
                                {/* The KB deletion dialog was here, but it's moved outside the Tabs component */}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* Document Deletion Dialog */}
            <Dialog open={isDeleteDocOpen} onOpenChange={setIsDeleteDocOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle className="text-destructive">Delete Document</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to delete <strong>{docToDelete?.name}</strong>?
                            This will remove the document and all its indexed chunks.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button
                            variant="outline"
                            onClick={() => setIsDeleteDocOpen(false)}
                            disabled={isDeletingDoc}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleDeleteDocument}
                            disabled={isDeletingDoc}
                        >
                            {isDeletingDoc && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Delete Document
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* KB Deletion Dialog */}
            <Dialog open={isDeleteConfirmOpen} onOpenChange={setIsDeleteConfirmOpen}>
                <DialogTrigger asChild>
                    <Button variant="destructive">
                        Delete KB
                    </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle className="text-destructive">Confirm Deletion</DialogTitle>
                        <DialogDescription>
                            This action is irreversible. This will permanently delete
                            <strong> {kb.name}</strong> and all indexed documents and vector chunks.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button
                            variant="outline"
                            onClick={() => setIsDeleteConfirmOpen(false)}
                            disabled={isDeletingKB}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleDelete}
                            disabled={isDeletingKB}
                        >
                            {isDeletingKB && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Confirm Delete
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Document Upload Dialog */}
            <DocumentUpload
                kbId={kbId}
                open={isUploadOpen}
                onOpenChange={setIsUploadOpen}
                onUploadComplete={loadDocuments}
            />

            {/* Document Preview Dialog */}
            <DocumentPreview
                document={docForPreview}
                open={isPreviewOpen}
                onOpenChange={setIsPreviewOpen}
            />
        </div>
    )
}
