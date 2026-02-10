"use client"

import { useEffect, useState } from "react"
import { KnowledgeBase } from "@/types/knowledge-base"
import { kbApi } from "@/lib/api/knowledge-base"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import {
    Plus,
    Loader2,
    Search,
    MoreHorizontal,
    ExternalLink,
    Settings,
    Trash2
} from "lucide-react"
import { Input } from "@/components/ui/input"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { toast } from "sonner"
import { useRouter } from "next/navigation"
import { Badge } from "@/components/ui/badge"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"

export default function KnowledgeBasesPage() {
    const [kbs, setKbs] = useState<KnowledgeBase[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState("")
    const [isCreateOpen, setIsCreateOpen] = useState(false)
    const [isCreating, setIsCreating] = useState(false)
    const router = useRouter()

    // Form state
    const [name, setName] = useState("")
    const [description, setDescription] = useState("")
    const [embeddingModel, setEmbeddingModel] = useState("multilingual-e5-large")

    useEffect(() => {
        loadKBs()
    }, [])

    const loadKBs = async () => {
        try {
            setIsLoading(true)
            const data = await kbApi.list()
            setKbs(data)
        } catch (error) {
            console.error(error)
            toast.error("Failed to load knowledge bases")
        } finally {
            setIsLoading(false)
        }
    }

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!name) return

        try {
            setIsCreating(true)
            const newKb = await kbApi.create({
                name,
                description,
                embedding_model: embeddingModel
            })
            toast.success("Knowledge base created successfully")
            setIsCreateOpen(false)
            setName("")
            setDescription("")
            setEmbeddingModel("multilingual-e5-large")
            setKbs([newKb, ...kbs])
        } catch (error) {
            console.error(error)
            toast.error("Failed to create knowledge base")
        } finally {
            setIsCreating(false)
        }
    }

    const filteredKBs = kbs.filter(kb =>
        kb.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        kb.description?.toLowerCase().includes(searchQuery.toLowerCase())
    )

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure you want to delete this knowledge base? All indexed data will be lost.")) return

        try {
            await kbApi.delete(id)
            toast.success("Knowledge base deleted")
            setKbs(kbs.filter(kb => kb.id !== id))
        } catch (error) {
            console.error(error)
            toast.error("Failed to delete knowledge base")
        }
    }

    if (isLoading) {
        return (
            <div className="flex h-full items-center justify-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    return (
        <div className="h-full flex-1 flex-col space-y-8 p-8 md:flex">
            <div className="flex items-center justify-between space-y-2">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">Knowledge Bases</h2>
                    <p className="text-muted-foreground">
                        Manage your organized knowledge and vector search configuration.
                    </p>
                </div>
                <div className="flex items-center space-x-2">
                    <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                        <DialogTrigger asChild>
                            <Button>
                                <Plus className="mr-2 h-4 w-4" /> Create Knowledge Base
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[425px]">
                            <DialogHeader>
                                <DialogTitle>Create Knowledge Base</DialogTitle>
                                <DialogDescription>
                                    Define a new knowledge base with specific embedding settings.
                                </DialogDescription>
                            </DialogHeader>
                            <form onSubmit={handleCreate}>
                                <div className="grid gap-4 py-4">
                                    <div className="grid gap-2">
                                        <Label htmlFor="name">Name</Label>
                                        <Input
                                            id="name"
                                            value={name}
                                            onChange={(e) => setName(e.target.value)}
                                            placeholder="e.g. Technical Specs"
                                            required
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <Label htmlFor="description">Description (Optional)</Label>
                                        <Input
                                            id="description"
                                            value={description}
                                            onChange={(e) => setDescription(e.target.value)}
                                            placeholder="What's this KB about?"
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <Label htmlFor="model">Embedding Model</Label>
                                        <select
                                            id="model"
                                            value={embeddingModel}
                                            onChange={(e) => setEmbeddingModel(e.target.value)}
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                            <option value="multilingual-e5-large">Multilingual E5 Large (Recommended)</option>
                                            <option value="multilingual-e5-base">Multilingual E5 Base (Faster)</option>
                                            <option value="text-embedding-3-small">OpenAI Text Embedding 3 Small</option>
                                            <option value="text-embedding-3-large">OpenAI Text Embedding 3 Large</option>
                                        </select>
                                    </div>
                                </div>
                                <DialogFooter>
                                    <Button type="submit" disabled={isCreating}>
                                        {isCreating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                        Create Knowledge Base
                                    </Button>
                                </DialogFooter>
                            </form>
                        </DialogContent>
                    </Dialog>
                </div>
            </div>

            <div className="flex items-center justify-between">
                <div className="flex flex-1 items-center space-x-2">
                    <div className="relative w-[300px]">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Filter knowledge bases..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-8"
                        />
                    </div>
                </div>
            </div>

            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Documents</TableHead>
                            <TableHead>Chunks</TableHead>
                            <TableHead>Model</TableHead>
                            <TableHead>Last Updated</TableHead>
                            <TableHead className="w-[100px]">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {filteredKBs.map((kb) => (
                            <TableRow key={kb.id} className="cursor-pointer" onClick={() => router.push(`/dashboard/kb/${kb.id}`)}>
                                <TableCell>
                                    <div className="flex flex-col">
                                        <span className="font-medium">{kb.name}</span>
                                        <span className="text-xs text-muted-foreground line-clamp-1">
                                            {kb.description}
                                        </span>
                                    </div>
                                </TableCell>
                                <TableCell>{kb.document_count}</TableCell>
                                <TableCell>{kb.chunk_count}</TableCell>
                                <TableCell>
                                    <Badge variant="outline" className="font-mono text-[10px]">
                                        {kb.embedding_model}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    {kb.updated_at ? new Date(kb.updated_at).toLocaleDateString() : 'N/A'}
                                </TableCell>
                                <TableCell onClick={(e) => e.stopPropagation()}>
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" className="h-8 w-8 p-0">
                                                <span className="sr-only">Open menu</span>
                                                <MoreHorizontal className="h-4 w-4" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                            <DropdownMenuItem onClick={() => router.push(`/dashboard/kb/${kb.id}`)}>
                                                <ExternalLink className="mr-2 h-4 w-4" />
                                                View details
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => router.push(`/dashboard/kb/${kb.id}/settings`)}>
                                                <Settings className="mr-2 h-4 w-4" />
                                                Settings
                                            </DropdownMenuItem>
                                            <DropdownMenuSeparator />
                                            <DropdownMenuItem
                                                className="text-destructive focus:text-destructive"
                                                onClick={() => handleDelete(kb.id)}
                                            >
                                                <Trash2 className="mr-2 h-4 w-4" />
                                                Delete
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </TableCell>
                            </TableRow>
                        ))}
                        {filteredKBs.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={6} className="h-24 text-center">
                                    {searchQuery ? "No matching knowledge bases found." : "No knowledge bases found."}
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    )
}
