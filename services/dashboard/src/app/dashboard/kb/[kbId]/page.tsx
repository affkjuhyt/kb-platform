"use client"

import { useEffect, useState, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { KnowledgeBase } from "@/types/knowledge-base"
import { kbApi } from "@/lib/api/knowledge-base"
import {
    Loader2,
    ArrowLeft,
    Database,
    FileText,
    BarChart3,
    Settings as SettingsIcon,
    AlertCircle
} from "lucide-react"
import { Button } from "@/components/ui/button"
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
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { KBAnalytics } from "@/components/kb-analytics"
import { formatDate, DATE_FORMATS } from "@/lib/utils/date"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"

export default function KBDetailPage() {
    const params = useParams()
    const router = useRouter()
    const kbId = params.kbId as string

    const [kb, setKb] = useState<KnowledgeBase | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false)
    const [isDeletingKB, setIsDeletingKB] = useState(false)

    useEffect(() => {
        if (kbId) {
            loadKB()
        }
    }, [kbId])

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

                <TabsContent value="documents">
                    <Card>
                        <CardHeader>
                            <CardTitle>Documents</CardTitle>
                            <CardDescription>Manage files indexed in this knowledge base.</CardDescription>
                        </CardHeader>
                        <CardContent className="h-[200px] flex items-center justify-center border-dashed border-2 rounded-lg m-4">
                            <p className="text-muted-foreground">Document list coming soon...</p>
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
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    )
}
