"use client"

import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { Search as SearchIcon, Loader2, Download, Settings2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { playgroundApi } from "@/lib/api/playground"
import { SearchResult } from "@/types/playground"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"

export default function SearchPlaygroundPage() {
    const searchParams = useSearchParams()
    const [query, setQuery] = useState("")
    const [kbId, setKbId] = useState("kb-1")
    const [topK, setTopK] = useState(10)
    const [threshold, setThreshold] = useState(0.7)
    const [results, setResults] = useState<SearchResult[]>([])
    const [isSearching, setIsSearching] = useState(false)
    const [queryTime, setQueryTime] = useState<number | null>(null)

    useEffect(() => {
        const q = searchParams.get('q')
        if (q) {
            setQuery(q)
            handleSearch(q)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const handleSearch = async (searchQuery?: string) => {
        const q = searchQuery || query
        if (!q.trim()) {
            toast.error("Please enter a search query")
            return
        }

        try {
            setIsSearching(true)
            const response = await playgroundApi.search({
                query: q,
                kb_id: kbId,
                top_k: topK,
                similarity_threshold: threshold,
            })
            setResults(response.results)
            setQueryTime(response.query_time_ms)
            toast.success(`Found ${response.total} results`)
        } catch (error) {
            console.error(error)
            toast.error("Search failed")
        } finally {
            setIsSearching(false)
        }
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
                                <Label htmlFor="kb">Knowledge Base</Label>
                                <Select value={kbId} onValueChange={setKbId}>
                                    <SelectTrigger id="kb">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="kb-1">Product Documentation</SelectItem>
                                        <SelectItem value="kb-2">Technical Guides</SelectItem>
                                        <SelectItem value="kb-3">Customer Support</SelectItem>
                                    </SelectContent>
                                </Select>
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

                            <div className="space-y-2">
                                <Label htmlFor="threshold">Similarity Threshold: {threshold.toFixed(2)}</Label>
                                <Slider
                                    id="threshold"
                                    min={0}
                                    max={1}
                                    step={0.05}
                                    value={[threshold]}
                                    onValueChange={([value]) => setThreshold(value)}
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
                                        key={result.id}
                                        className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
                                    >
                                        <div className="flex items-start justify-between gap-4">
                                            <div className="flex-1 space-y-2">
                                                <div className="flex items-center gap-2">
                                                    <Badge variant="outline">#{idx + 1}</Badge>
                                                    <span className="text-sm font-medium">
                                                        {result.metadata.document_name}
                                                    </span>
                                                    <Badge variant="secondary">
                                                        Score: {result.score.toFixed(3)}
                                                    </Badge>
                                                </div>
                                                <p className="text-sm leading-relaxed">{result.content}</p>
                                                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                                    <span>Chunk {result.metadata.chunk_index}</span>
                                                    <span>Source: {result.metadata.source}</span>
                                                    <span>
                                                        {formatDistanceToNow(new Date(result.metadata.created_at), {
                                                            addSuffix: true,
                                                        })}
                                                    </span>
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
