"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@/context/auth-context"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Loader2, AlertCircle } from "lucide-react"
import axios from "axios"
import { formatDistanceToNow } from "date-fns"

interface AuditLogEntry {
    id: string
    timestamp: string
    method: string
    path: string
    status_code: number
    duration_ms: number
    client_ip: string
    user_email?: string
}

export function AuditLogsTable() {
    const { user } = useAuth()
    const [logs, setLogs] = useState<AuditLogEntry[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const fetchLogs = async () => {
            try {
                setLoading(true)
                // Note: This endpoint requires "admin" permission which "owner" role now has
                const response = await axios.get("/admin/audit-logs?limit=20")
                setLogs(response.data.logs)
            } catch (err: unknown) {
                console.error("Failed to fetch audit logs:", err)
                if (axios.isAxiosError(err)) {
                    setError(err.response?.status === 403
                        ? "You do not have permission to view audit logs."
                        : "Failed to load audit logs.")
                } else {
                    setError("Failed to load audit logs.")
                }
            } finally {
                setLoading(false)
            }
        }

        if (user) {
            fetchLogs()
        }
    }, [user])

    const getMethodColor = (method: string) => {
        switch (method) {
            case "GET": return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
            case "POST": return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
            case "PUT": return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300"
            case "DELETE": return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
            default: return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300"
        }
    }

    const getStatusColor = (status: number) => {
        if (status >= 500) return "text-red-600 dark:text-red-400 font-bold"
        if (status >= 400) return "text-orange-600 dark:text-orange-400 font-bold"
        if (status >= 300) return "text-blue-600 dark:text-blue-400"
        return "text-green-600 dark:text-green-400"
    }

    if (loading) {
        return (
            <div className="flex h-40 items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex h-40 items-center justify-center text-muted-foreground gap-2">
                <AlertCircle className="h-5 w-5" />
                <span>{error}</span>
            </div>
        )
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Audit Logs</CardTitle>
                <CardDescription>
                    Recent activity in your workspace
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="rounded-md border">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Time</TableHead>
                                <TableHead>Method</TableHead>
                                <TableHead>Path</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Duration</TableHead>
                                <TableHead className="text-right">IP Address</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {logs.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-24 text-center">
                                        No logs found.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                logs.map((log) => (
                                    <TableRow key={log.id}>
                                        <TableCell className="font-mono text-xs whitespace-nowrap">
                                            {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className={`border-0 ${getMethodColor(log.method)}`}>
                                                {log.method}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="font-mono text-xs max-w-[200px] truncate" title={log.path}>
                                            {log.path}
                                        </TableCell>
                                        <TableCell className={getStatusColor(log.status_code)}>
                                            {log.status_code}
                                        </TableCell>
                                        <TableCell className="text-muted-foreground text-xs">
                                            {log.duration_ms.toFixed(0)}ms
                                        </TableCell>
                                        <TableCell className="text-right font-mono text-xs text-muted-foreground">
                                            {log.client_ip}
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </div>
            </CardContent>
        </Card>
    )
}
