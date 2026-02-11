"use client"

import { useState, useEffect, useCallback } from "react"
import { useSearchParams } from "next/navigation"
import { Search as SearchIcon, Loader2, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { playgroundApi } from "@/lib/api/playground"
import { getTenantId } from "@/lib/api/client"
import { SearchResult } from "@/types/playground"
import { toast } from "sonner"

import { Suspense } from "react"
// ... imports

function SearchPlaygroundContent() {
    const searchParams = useSearchParams()
    // ... logic ...
    const [query, setQuery] = useState("")
    const [tenantId, setTenantId] = useState(getTenantId() || "default")
    const [topK, setTopK] = useState(10)
    const [results, setResults] = useState<SearchResult[]>([])
    const [isSearching, setIsSearching] = useState(false)
    const [queryTime, setQueryTime] = useState<number | null>(null)

    const runSearch = useCallback(async (searchQuery?: string) => {
        const q = searchQuery || query
        if (!q.trim()) {
            toast.error("Please enter a search query")
            return
        }

        try {
            setIsSearching(true)
            const startTime = Date.now()
            const response = await playgroundApi.search({
                query: q,
                tenant_id: tenantId,
                top_k: topK,
            })
            setResults(response.results)
            setQueryTime(Date.now() - startTime)
            toast.success(`Found ${response.results.length} results`)
        } catch (error) {
            console.error(error)
            toast.error("Search failed")
        } finally {
            setIsSearching(false)
        }
    }, [query, tenantId, topK])

    useEffect(() => {
        const q = searchParams.get('q')
        if (q) {
            setQuery(q)
            runSearch(q)
        }
    }, [runSearch, searchParams])

    const handleSearch = () => {
        runSearch()
    }

    const handleExport = () => {
        const data = JSON.stringify({ query, results, query_time_ms: queryTime }, null, 2)
        const blob = new Blob([data], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `search-results-${Date.now()}.json`
        a.click()
        URL.revokeObjectURL(url)
        toast.success("Results exported")
    }

    return (
        <div className="container mx-auto p-6 max-w-7xl">
            <div className="space-y-6">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold">Search Playground</h1>
                    <p className="text-muted-foreground mt-1">
                        Test search queries and explore results with detailed metadata
                    </p>
                </div>

                {/* Search Controls */}
                <Card>
                    <CardHeader>
                        <CardTitle>Query Configuration</CardTitle>
                        <CardDescription>Configure your search parameters</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* Query Input */}
                        <div className="space-y-2">
                            <Label htmlFor="query">Search Query</Label>
                            <div className="flex gap-2">
                                <Input
                                    id="query"
                                    placeholder="Enter your search query..."
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                                    className="flex-1"
                                />
                                <Button onClick={() => handleSearch()} disabled={isSearching}>
                                    {isSearching ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <SearchIcon className="h-4 w-4" />
                                    )}
                                    <span className="ml-2">Search</span>
                                </Button>
                            </div>
                        </div>

                        {/* Filters */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="tenant">Tenant ID</Label>
                                <Input
                                    id="tenant"
                                    value={tenantId}
                                    onChange={(e) => setTenantId(e.target.value)}
                                    placeholder="Enter tenant ID"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="topk">Top K Results: {topK}</Label>
                                <Slider
                                    id="topk"
                                    min={1}
                                    max={50}
                                    step={1}
                                    value={[topK]}
                                    onValueChange={([value]) => setTopK(value)}
                                />
                            </div>


                        </div>
                    </CardContent>
                </Card>

                {/* Results */}
                {results.length > 0 && (
                    <Card>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle>Search Results</CardTitle>
                                    <CardDescription>
                                        {results.length} results • Query time: {queryTime}ms
                                    </CardDescription>
                                </div>
                                <Button variant="outline" size="sm" onClick={handleExport}>
                                    <Download className="h-4 w-4 mr-2" />
                                    Export
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {results.map((result, idx) => (
                                    <div
                                        key={`${result.doc_id}-${result.chunk_index}`}
                                        className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
                                    >
                                        <div className="flex items-start justify-between gap-4">
                                            <div className="flex-1 space-y-2">
                                                <div className="flex items-center gap-2">
                                                    <Badge variant="outline">#{idx + 1}</Badge>
                                                    <span className="text-sm font-medium">
                                                        {result.source_id}
                                                    </span>
                                                    <Badge variant="secondary">
                                                        Score: {result.score.toFixed(3)}
                                                    </Badge>
                                                </div>
                                                <p className="text-sm leading-relaxed">{result.text}</p>
                                                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                                    <span>Chunk {result.chunk_index}</span>
                                                    <span>Source: {result.source}</span>
                                                    <span>Section: {result.section_path}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Empty State */}
                {!isSearching && results.length === 0 && (
                    <Card>
                        <CardContent className="flex flex-col items-center justify-center py-12">
                            <SearchIcon className="h-12 w-12 text-muted-foreground mb-4" />
                            <p className="text-muted-foreground text-center">
                                Enter a query above to start searching
                            </p>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    )
}

export default function SearchPlaygroundPage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-8"><Loader2 className="h-6 w-6 animate-spin" /></div>}>
            <SearchPlaygroundContent />
        </Suspense>
    )
}
