"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import {
    FileText,
    Loader2,
    Search,
    Upload,
    Trash2,
    Eye,
    MoreHorizontal,
    Database,
    AlertCircle,
    CheckCircle2,
    Clock,
    XCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"
import { toast } from "sonner"
import { KnowledgeBase } from "@/types/knowledge-base"
import { Document, DocumentStatus } from "@/types/document"
import { kbApi } from "@/lib/api/knowledge-base"
import { documentApi } from "@/lib/api/document"
import { formatDate } from "@/lib/utils/date"
import { formatFileSize } from "@/lib/utils/format"
import { DocumentUpload } from "@/components/document-upload"
import { DocumentPreview } from "@/components/document-preview"

// Extend Document with KB info for the unified view
interface DocumentWithKB extends Document {
    kb_name: string
}

export default function DocumentsPage() {
    const router = useRouter()

    // Data state
    const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
    const [allDocuments, setAllDocuments] = useState<DocumentWithKB[]>([])
    const [isLoading, setIsLoading] = useState(true)

    // Filter state
    const [searchQuery, setSearchQuery] = useState("")
    const [filterKB, setFilterKB] = useState<string>("all")
    const [filterStatus, setFilterStatus] = useState<string>("all")

    // Selection state
    const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set())

    // Upload state
    const [isUploadOpen, setIsUploadOpen] = useState(false)
    const [uploadKbId, setUploadKbId] = useState<string>("")

    // Preview state
    const [docForPreview, setDocForPreview] = useState<Document | null>(null)
    const [isPreviewOpen, setIsPreviewOpen] = useState(false)

    // Delete state
    const [docToDelete, setDocToDelete] = useState<DocumentWithKB | null>(null)
    const [isDeleteOpen, setIsDeleteOpen] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)

    // ─── Load Data ────────────────────────────────────────────────────

    const loadData = useCallback(async () => {
        try {
            setIsLoading(true)

            // 1. Fetch all knowledge bases
            const kbs = await kbApi.list()
            setKnowledgeBases(kbs)

            // Set default upload KB
            if (kbs.length > 0 && !uploadKbId) {
                setUploadKbId(kbs[0].id)
            }

            // 2. Fetch documents from each KB in parallel
            const docsPerKB = await Promise.all(
                kbs.map(async (kb) => {
                    try {
                        const docs = await documentApi.list(kb.id)
                        return docs.map((doc): DocumentWithKB => ({
                            ...doc,
                            kb_id: kb.id,
                            kb_name: kb.name,
                        }))
                    } catch {
                        // If a KB's documents fail to load, skip it
                        return [] as DocumentWithKB[]
                    }
                })
            )

            setAllDocuments(docsPerKB.flat())
        } catch (error) {
            console.error("Failed to load data:", error)
            toast.error("Failed to load documents")
        } finally {
            setIsLoading(false)
        }
    }, [uploadKbId])

    useEffect(() => {
        loadData()
    }, [loadData])

    // ─── Filtering ────────────────────────────────────────────────────

    const filteredDocs = useMemo(() => {
        return allDocuments.filter((doc) => {
            // Text search
            if (searchQuery && !doc.name.toLowerCase().includes(searchQuery.toLowerCase())) {
                return false
            }
            // KB filter
            if (filterKB !== "all" && doc.kb_id !== filterKB) {
                return false
            }
            // Status filter
            if (filterStatus !== "all" && doc.status !== filterStatus) {
                return false
            }
            return true
        })
    }, [allDocuments, searchQuery, filterKB, filterStatus])

    // ─── Stats ────────────────────────────────────────────────────────

    const stats = useMemo(() => {
        const total = allDocuments.length
        const processing = allDocuments.filter(d => d.status === DocumentStatus.PROCESSING || d.status === DocumentStatus.PENDING).length
        const completed = allDocuments.filter(d => d.status === DocumentStatus.COMPLETED).length
        const failed = allDocuments.filter(d => d.status === DocumentStatus.FAILED).length
        return { total, processing, completed, failed, kbCount: knowledgeBases.length }
    }, [allDocuments, knowledgeBases])

    // ─── Selection Handlers ───────────────────────────────────────────

    const toggleDocSelection = (docId: string) => {
        setSelectedDocs((prev) => {
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
        if (selectedDocs.size === filteredDocs.length && filteredDocs.length > 0) {
            setSelectedDocs(new Set())
        } else {
            setSelectedDocs(new Set(filteredDocs.map(d => d.id)))
        }
    }

    // ─── Delete Handlers ──────────────────────────────────────────────

    const handleDeleteDocument = async () => {
        if (!docToDelete) return

        try {
            setIsDeleting(true)
            await documentApi.delete(docToDelete.id)
            toast.success(`Deleted "${docToDelete.name}"`)
            setAllDocuments(prev => prev.filter(d => d.id !== docToDelete.id))
            setSelectedDocs(prev => {
                const next = new Set(prev)
                next.delete(docToDelete.id)
                return next
            })
            setIsDeleteOpen(false)
            setDocToDelete(null)
        } catch (error) {
            console.error(error)
            toast.error("Failed to delete document")
        } finally {
            setIsDeleting(false)
        }
    }

    const handleBulkDelete = async () => {
        if (selectedDocs.size === 0) return

        const count = selectedDocs.size
        try {
            for (const docId of Array.from(selectedDocs)) {
                await documentApi.delete(docId)
            }
            toast.success(`Deleted ${count} document${count > 1 ? "s" : ""}`)
            setAllDocuments(prev => prev.filter(d => !selectedDocs.has(d.id)))
            setSelectedDocs(new Set())
        } catch (error) {
            console.error(error)
            toast.error("Failed to delete some documents")
        }
    }

    // ─── Status Badge ─────────────────────────────────────────────────

    const getStatusBadge = (status: DocumentStatus) => {
        const variants: Record<DocumentStatus, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
            [DocumentStatus.PENDING]: { variant: "secondary", label: "Pending" },
            [DocumentStatus.PROCESSING]: { variant: "default", label: "Processing" },
            [DocumentStatus.COMPLETED]: { variant: "outline", label: "Completed" },
            [DocumentStatus.FAILED]: { variant: "destructive", label: "Failed" },
            [DocumentStatus.ARCHIVED]: { variant: "secondary", label: "Archived" },
        }
        const config = variants[status]
        return <Badge variant={config.variant}>{config.label}</Badge>
    }

    // ─── Upload Handlers ──────────────────────────────────────────────

    const openUploadDialog = () => {
        if (knowledgeBases.length === 0) {
            toast.error("No knowledge bases found. Create one first.")
            return
        }
        if (!uploadKbId && knowledgeBases.length > 0) {
            setUploadKbId(knowledgeBases[0].id)
        }
        setIsUploadOpen(true)
    }

    // ─── Render ───────────────────────────────────────────────────────

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-full p-8">
                <div className="flex flex-col items-center gap-3">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Loading documents from all knowledge bases...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="h-full flex-1 flex-col space-y-6 p-8 md:flex">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
                    <p className="text-muted-foreground mt-1">
                        Browse and manage documents across all knowledge bases
                    </p>
                </div>
                <Button onClick={openUploadDialog}>
                    <Upload className="mr-2 h-4 w-4" /> Upload Documents
                </Button>
            </div>

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
                        <FileText className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.total}</div>
                        <p className="text-xs text-muted-foreground">
                            Across {stats.kbCount} knowledge base{stats.kbCount !== 1 ? "s" : ""}
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Knowledge Bases</CardTitle>
                        <Database className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.kbCount}</div>
                        <p className="text-xs text-muted-foreground">Active repositories</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Completed</CardTitle>
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.completed}</div>
                        <p className="text-xs text-muted-foreground">Successfully indexed</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Processing</CardTitle>
                        <Clock className="h-4 w-4 text-yellow-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.processing}</div>
                        <p className="text-xs text-muted-foreground">Being indexed</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Failed</CardTitle>
                        <XCircle className="h-4 w-4 text-destructive" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.failed}</div>
                        <p className="text-xs text-muted-foreground">Need attention</p>
                    </CardContent>
                </Card>
            </div>

            {/* Filters & Search */}
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="flex flex-1 items-center gap-4">
                    <div className="relative w-[280px]">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search documents..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-8"
                        />
                    </div>
                    <Select value={filterKB} onValueChange={setFilterKB}>
                        <SelectTrigger className="w-[200px]">
                            <SelectValue placeholder="All Knowledge Bases" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Knowledge Bases</SelectItem>
                            {knowledgeBases.map(kb => (
                                <SelectItem key={kb.id} value={kb.id}>{kb.name}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Select value={filterStatus} onValueChange={setFilterStatus}>
                        <SelectTrigger className="w-[160px]">
                            <SelectValue placeholder="All Statuses" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Statuses</SelectItem>
                            <SelectItem value={DocumentStatus.PENDING}>Pending</SelectItem>
                            <SelectItem value={DocumentStatus.PROCESSING}>Processing</SelectItem>
                            <SelectItem value={DocumentStatus.COMPLETED}>Completed</SelectItem>
                            <SelectItem value={DocumentStatus.FAILED}>Failed</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {/* Upload KB Selector (visible when upload dialog is about to open) */}
                {knowledgeBases.length > 0 && (
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground whitespace-nowrap">Upload to:</span>
                        <Select value={uploadKbId} onValueChange={setUploadKbId}>
                            <SelectTrigger className="w-[180px]">
                                <SelectValue placeholder="Select KB" />
                            </SelectTrigger>
                            <SelectContent>
                                {knowledgeBases.map(kb => (
                                    <SelectItem key={kb.id} value={kb.id}>{kb.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                )}
            </div>

            {/* Document Table */}
            <Card>
                <CardHeader>
                    <CardTitle>Documents</CardTitle>
                    <CardDescription>
                        {filteredDocs.length} document{filteredDocs.length !== 1 ? "s" : ""}
                        {filterKB !== "all" || filterStatus !== "all" || searchQuery
                            ? " (filtered)"
                            : ` across ${stats.kbCount} knowledge base${stats.kbCount !== 1 ? "s" : ""}`}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {filteredDocs.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-40 text-center">
                            <FileText className="h-12 w-12 text-muted-foreground mb-3" />
                            <p className="text-muted-foreground">
                                {allDocuments.length === 0
                                    ? "No documents uploaded yet. Upload your first document to get started."
                                    : "No documents match your filters."}
                            </p>
                            {allDocuments.length === 0 && (
                                <Button variant="outline" className="mt-4" onClick={openUploadDialog}>
                                    <Upload className="mr-2 h-4 w-4" /> Upload Document
                                </Button>
                            )}
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
                                    <TableHead>Knowledge Base</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Size</TableHead>
                                    <TableHead>Chunks</TableHead>
                                    <TableHead>Version</TableHead>
                                    <TableHead>Updated</TableHead>
                                    <TableHead className="w-[80px]">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredDocs.map((doc) => (
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
                                                <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                                <span className="font-medium truncate max-w-[200px]">{doc.name}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <button
                                                className="text-sm text-primary hover:underline cursor-pointer bg-transparent border-none p-0"
                                                onClick={() => router.push(`/dashboard/kb/${doc.kb_id}`)}
                                            >
                                                {doc.kb_name}
                                            </button>
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
                                                    <DropdownMenuItem
                                                        onClick={() => {
                                                            setDocForPreview(doc)
                                                            setIsPreviewOpen(true)
                                                        }}
                                                    >
                                                        <Eye className="mr-2 h-4 w-4" />
                                                        Preview
                                                    </DropdownMenuItem>
                                                    <DropdownMenuItem
                                                        onClick={() => router.push(`/dashboard/kb/${doc.kb_id}`)}
                                                    >
                                                        <Database className="mr-2 h-4 w-4" />
                                                        Go to KB
                                                    </DropdownMenuItem>
                                                    <DropdownMenuSeparator />
                                                    <DropdownMenuItem
                                                        className="text-destructive focus:text-destructive"
                                                        onClick={() => {
                                                            setDocToDelete(doc)
                                                            setIsDeleteOpen(true)
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
                        {selectedDocs.size} item{selectedDocs.size !== 1 ? "s" : ""} selected
                    </span>
                    <Separator orientation="vertical" className="h-4" />
                    <div className="flex items-center gap-2">
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

            {/* Delete Confirmation Dialog */}
            <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle className="text-destructive">Delete Document</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to delete <strong>{docToDelete?.name}</strong>
                            {docToDelete && (
                                <> from <strong>{docToDelete.kb_name}</strong></>
                            )}?
                            This will remove the document and all its indexed chunks.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button
                            variant="outline"
                            onClick={() => setIsDeleteOpen(false)}
                            disabled={isDeleting}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleDeleteDocument}
                            disabled={isDeleting}
                        >
                            {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Delete Document
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Document Upload Dialog */}
            <DocumentUpload
                kbId={uploadKbId}
                open={isUploadOpen}
                onOpenChange={setIsUploadOpen}
                onUploadComplete={loadData}
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
