"use client"

import { useEffect, useState } from "react"
import { kbApi } from "@/lib/api/knowledge-base"
import { Loader2, FileText, Database } from "lucide-react"

export default function DashboardPage() {
    const [stats, setStats] = useState({
        totalDocs: 0,
        totalKBs: 0,
        loading: true
    })

    useEffect(() => {
        async function loadStats() {
            try {
                const kbs = await kbApi.list()
                const totalDocs = kbs.reduce((sum, kb) => sum + kb.document_count, 0)
                setStats({
                    totalDocs,
                    totalKBs: kbs.length,
                    loading: false
                })
            } catch (error) {
                console.error("Failed to load dashboard stats", error)
                setStats(s => ({ ...s, loading: false }))
            }
        }
        loadStats()
    }, [])

    return (
        <div className="space-y-6">
            <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="p-6 border rounded-xl bg-card text-card-foreground shadow-sm flex flex-col justify-between">
                    <div className="flex items-center justify-between space-y-0 pb-2">
                        <span className="text-sm font-medium text-muted-foreground">Total Documents</span>
                        <FileText className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="text-2xl font-bold">
                        {stats.loading ? (
                            <Loader2 className="h-6 w-6 animate-spin" />
                        ) : (
                            stats.totalDocs
                        )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">Across all knowledge bases</p>
                </div>
                <div className="p-6 border rounded-xl bg-card text-card-foreground shadow-sm flex flex-col justify-between">
                    <div className="flex items-center justify-between space-y-0 pb-2">
                        <span className="text-sm font-medium text-muted-foreground">Active Knowledge Bases</span>
                        <Database className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="text-2xl font-bold">
                        {stats.loading ? (
                            <Loader2 className="h-6 w-6 animate-spin" />
                        ) : (
                            stats.totalKBs
                        )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">Ready for queries</p>
                </div>
            </div>
        </div>
    )
}
