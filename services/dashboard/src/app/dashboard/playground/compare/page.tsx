"use client"

import { useState } from "react"
import { GitCompare, Loader2, Play } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { playgroundApi } from "@/lib/api/playground"
import { getTenantId } from "@/lib/api/client"
import { ComparisonResult } from "@/types/playground"
import { toast } from "sonner"

const AVAILABLE_MODELS = [
    { id: "gpt-4", name: "GPT-4" },
    { id: "gpt-3.5-turbo", name: "GPT-3.5 Turbo" },
    { id: "claude-3-opus", name: "Claude 3 Opus" },
    { id: "claude-3-sonnet", name: "Claude 3 Sonnet" },
]

export default function ComparePlaygroundPage() {
    const [query, setQuery] = useState("")
    const [tenantId, setTenantId] = useState(getTenantId() || "default")
    const [selectedModels, setSelectedModels] = useState<string[]>(["gpt-4", "claude-3-sonnet"])
    const [results, setResults] = useState<ComparisonResult[]>([])
    const [isComparing, setIsComparing] = useState(false)
    const [totalTime, setTotalTime] = useState<number | null>(null)

    const handleCompare = async () => {
        if (!query.trim()) {
            toast.error("Please enter a query")
            return
        }

        if (selectedModels.length < 2) {
            toast.error("Please select at least 2 models to compare")
            return
        }

        try {
            setIsComparing(true)
            setResults([])

            const response = await playgroundApi.compare({
                query,
                tenant_id: tenantId,
                models: selectedModels,
            })

            setResults(response.results)
            setTotalTime(response.total_time_ms)
            toast.success("Comparison complete")
        } catch (error) {
            console.error(error)
            toast.error("Comparison failed")
        } finally {
            setIsComparing(false)
        }
    }

    const toggleModel = (modelId: string) => {
        setSelectedModels(prev =>
            prev.includes(modelId)
                ? prev.filter(id => id !== modelId)
                : [...prev, modelId]
        )
    }

    return (
        <div className="container mx-auto p-6 max-w-7xl">
            <div className="space-y-6">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold">Compare Mode</h1>
                    <p className="text-muted-foreground mt-1">
                        Compare outputs from different models side-by-side
                    </p>
                </div>

                {/* Configuration */}
                <Card>
                    <CardHeader>
                        <CardTitle>Comparison Configuration</CardTitle>
                        <CardDescription>Select models and enter your query</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="tenant-compare">Tenant ID</Label>
                                <Input
                                    id="tenant-compare"
                                    value={tenantId}
                                    onChange={(e) => setTenantId(e.target.value)}
                                    placeholder="Enter tenant ID"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label>Models to Compare ({selectedModels.length} selected)</Label>
                                <div className="grid grid-cols-2 gap-2">
                                    {AVAILABLE_MODELS.map((model) => (
                                        <div key={model.id} className="flex items-center space-x-2">
                                            <Checkbox
                                                id={model.id}
                                                checked={selectedModels.includes(model.id)}
                                                onCheckedChange={() => toggleModel(model.id)}
                                            />
                                            <label
                                                htmlFor={model.id}
                                                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                                            >
                                                {model.name}
                                            </label>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="query-compare">Query</Label>
                            <Textarea
                                id="query-compare"
                                placeholder="What is vector search and how does it work?"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                rows={3}
                            />
                        </div>

                        <Button onClick={handleCompare} disabled={isComparing} className="w-full">
                            {isComparing ? (
                                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            ) : (
                                <Play className="h-4 w-4 mr-2" />
                            )}
                            Run Comparison
                        </Button>
                    </CardContent>
                </Card>

                {/* Results */}
                {results.length > 0 && (
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-semibold">Comparison Results</h2>
                            <Badge variant="outline">Total time: {totalTime}ms</Badge>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {results.map((result, idx) => (
                                <Card key={idx}>
                                    <CardHeader>
                                        <div className="flex items-center justify-between">
                                            <CardTitle className="text-lg">{result.model}</CardTitle>
                                            <div className="flex gap-2">
                                                <Badge variant="secondary">Confidence: {(result.confidence * 100).toFixed(0)}%</Badge>
                                                <Badge variant="outline">{result.response_time_ms}ms</Badge>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div>
                                            <h4 className="text-sm font-medium mb-2">Answer</h4>
                                            <ScrollArea className="h-[300px]">
                                                <div className="prose prose-sm dark:prose-invert max-w-none pr-4">
                                                    <p className="whitespace-pre-wrap leading-relaxed text-sm">
                                                        {result.answer}
                                                    </p>
                                                </div>
                                            </ScrollArea>
                                        </div>

                                        <Separator />

                                        <div>
                                            <h4 className="text-sm font-medium mb-2">
                                                Citations ({result.citations.length})
                                            </h4>
                                            <div className="space-y-2">
                                                {result.citations.slice(0, 3).map((citation, cidx) => (
                                                    <div
                                                        key={`${citation.doc_id}-${cidx}`}
                                                        className="text-xs border rounded p-2"
                                                    >
                                                        <div className="flex items-center gap-2 mb-1">
                                                            <Badge variant="outline" className="text-xs">
                                                                [{cidx + 1}]
                                                            </Badge>
                                                            <span className="font-medium truncate">
                                                                {citation.source_id}
                                                            </span>
                                                        </div>
                                                        <p className="text-muted-foreground line-clamp-2">
                                                            {citation.section_path}
                                                        </p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </div>
                )}

                {/* Empty State */}
                {!isComparing && results.length === 0 && (
                    <Card>
                        <CardContent className="flex flex-col items-center justify-center py-12">
                            <GitCompare className="h-12 w-12 text-muted-foreground mb-4" />
                            <p className="text-muted-foreground text-center">
                                Select models and run a comparison to see results
                            </p>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    )
}
