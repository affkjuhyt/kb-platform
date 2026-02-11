"use client"

import { useState, useEffect } from "react"
import { DataSource, DataSourceType, DataSourceStatus } from "@/types/data-source"
import { dataSourceApi } from "@/lib/api/data-source"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
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
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Globe, Link2, FolderSync, MoreVertical, Play, Pause, RefreshCw, Trash2, Loader2, AlertTriangle } from "lucide-react"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog"

interface DataSourcesListProps {
    kbId: string
}

export function DataSourcesList({ kbId }: DataSourcesListProps) {
    const [dataSources, setDataSources] = useState<DataSource[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [filter, setFilter] = useState<DataSourceType | 'all'>('all')
    const [sourceToDelete, setSourceToDelete] = useState<string | null>(null)
    const [isDeleting, setIsDeleting] = useState(false)

    useEffect(() => {
        loadDataSources()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [kbId])

    const loadDataSources = async () => {
        try {
            setIsLoading(true)
            const data = await dataSourceApi.list(kbId)
            setDataSources(data)
        } catch (error) {
            console.error(error)
            toast.error("Failed to load data sources")
        } finally {
            setIsLoading(false)
        }
    }

    const handlePause = async (sourceId: string) => {
        try {
            const updatedSource = await dataSourceApi.pause(sourceId)
            setDataSources(prev => prev.map(ds => ds.id === sourceId ? updatedSource : ds))
            toast.success("Data source paused")
        } catch (error) {
            console.error(error)
            toast.error("Failed to pause data source")
        }
    }

    const handleResume = async (sourceId: string) => {
        try {
            const updatedSource = await dataSourceApi.resume(sourceId)
            setDataSources(prev => prev.map(ds => ds.id === sourceId ? updatedSource : ds))
            toast.success("Data source resumed")
        } catch (error) {
            console.error(error)
            toast.error("Failed to resume data source")
        }
    }

    const handleTriggerSync = async (sourceId: string) => {
        try {
            const updatedSource = await dataSourceApi.triggerSync(sourceId)
            setDataSources(prev => prev.map(ds => ds.id === sourceId ? updatedSource : ds))
            toast.success("Sync triggered")
        } catch (error) {
            console.error(error)
            toast.error("Failed to trigger sync")
        }
    }

    const handleDelete = (sourceId: string) => {
        setSourceToDelete(sourceId)
    }

    const confirmDelete = async () => {
        if (!sourceToDelete) return

        try {
            setIsDeleting(true)
            await dataSourceApi.delete(sourceToDelete)
            setDataSources(prev => prev.filter(ds => ds.id !== sourceToDelete))
            toast.success("Data source deleted")
        } catch (error) {
            console.error(error)
            toast.error("Failed to delete data source")
        } finally {
            setIsDeleting(false)
            setSourceToDelete(null)
        }
    }

    const getTypeIcon = (type: DataSourceType) => {
        switch (type) {
            case DataSourceType.WEB_CRAWLER:
                return <Globe className="h-4 w-4" />
            case DataSourceType.API_CONNECTOR:
                return <Link2 className="h-4 w-4" />
            case DataSourceType.FILE_WATCHER:
                return <FolderSync className="h-4 w-4" />
        }
    }

    const getStatusBadge = (status: DataSourceStatus) => {
        const variants: Record<DataSourceStatus, "default" | "secondary" | "destructive" | "outline"> = {
            [DataSourceStatus.ACTIVE]: "default",
            [DataSourceStatus.PAUSED]: "secondary",
            [DataSourceStatus.ERROR]: "destructive",
            [DataSourceStatus.SYNCING]: "outline",
        }

        return (
            <Badge variant={variants[status]}>
                {status === DataSourceStatus.SYNCING && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                {status}
            </Badge>
        )
    }

    const filteredSources = filter === 'all'
        ? dataSources
        : dataSources.filter(ds => ds.type === filter)

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <Select value={filter} onValueChange={(value: string) => setFilter(value as DataSourceType | 'all')}>
                    <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="Filter by type" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All Types</SelectItem>
                        <SelectItem value={DataSourceType.WEB_CRAWLER}>Web Crawler</SelectItem>
                        <SelectItem value={DataSourceType.API_CONNECTOR}>API Connector</SelectItem>
                        <SelectItem value={DataSourceType.FILE_WATCHER}>File Watcher</SelectItem>
                    </SelectContent>
                </Select>
                <Button>
                    Add Data Source
                </Button>
            </div>

            {filteredSources.length === 0 ? (
                <div className="border-2 border-dashed rounded-lg p-12 text-center">
                    <p className="text-muted-foreground">
                        No data sources found. Add one to start automated ingestion.
                    </p>
                </div>
            ) : (
                <div className="border rounded-lg">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Type</TableHead>
                                <TableHead>Name</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Last Sync</TableHead>
                                <TableHead>Next Sync</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredSources.map((source) => (
                                <TableRow key={source.id}>
                                    <TableCell>
                                        <div className="flex items-center gap-2">
                                            {getTypeIcon(source.type)}
                                            <span className="text-sm capitalize">
                                                {source.type.replace('_', ' ')}
                                            </span>
                                        </div>
                                    </TableCell>
                                    <TableCell className="font-medium">{source.name}</TableCell>
                                    <TableCell>{getStatusBadge(source.status)}</TableCell>
                                    <TableCell className="text-sm text-muted-foreground">
                                        {source.last_sync
                                            ? formatDistanceToNow(new Date(source.last_sync), { addSuffix: true })
                                            : 'Never'
                                        }
                                    </TableCell>
                                    <TableCell className="text-sm text-muted-foreground">
                                        {source.next_sync
                                            ? formatDistanceToNow(new Date(source.next_sync), { addSuffix: true })
                                            : '-'
                                        }
                                    </TableCell>
                                    <TableCell className="text-right">
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button variant="ghost" size="sm">
                                                    <MoreVertical className="h-4 w-4" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end">
                                                <DropdownMenuItem onClick={() => handleTriggerSync(source.id)}>
                                                    <RefreshCw className="mr-2 h-4 w-4" />
                                                    Trigger Sync
                                                </DropdownMenuItem>
                                                {source.status === DataSourceStatus.ACTIVE ? (
                                                    <DropdownMenuItem onClick={() => handlePause(source.id)}>
                                                        <Pause className="mr-2 h-4 w-4" />
                                                        Pause
                                                    </DropdownMenuItem>
                                                ) : (
                                                    <DropdownMenuItem onClick={() => handleResume(source.id)}>
                                                        <Play className="mr-2 h-4 w-4" />
                                                        Resume
                                                    </DropdownMenuItem>
                                                )}
                                                <DropdownMenuItem
                                                    onClick={() => handleDelete(source.id)}
                                                    className="text-destructive"
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
                </div>
            )}

            <AlertDialog open={!!sourceToDelete} onOpenChange={(open) => !open && setSourceToDelete(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2">
                            <AlertTriangle className="h-5 w-5 text-destructive" />
                            Delete Data Source
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete this data source? This action cannot be undone and will stop all automated ingestion from this source.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(e: React.MouseEvent) => {
                                e.preventDefault()
                                confirmDelete()
                            }}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            disabled={isDeleting}
                        >
                            {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    )
}
