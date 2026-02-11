"use client"

import { useState } from "react"
import { MessageSquare, Loader2, Copy, Check, BookOpen, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
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
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { playgroundApi } from "@/lib/api/playground"
import { Citation } from "@/types/playground"
import { toast } from "sonner"

export default function RAGPlaygroundPage() {
    const [query, setQuery] = useState("")
    const [kbId, setKbId] = useState("kb-1")
    const [model, setModel] = useState("gpt-4")
    const [temperature, setTemperature] = useState(0.7)
    const [topK, setTopK] = useState(5)
    const [systemPrompt, setSystemPrompt] = useState(
        "You are a helpful assistant. Answer the question based on the provided context. Be concise and accurate."
    )
    const [answer, setAnswer] = useState("")
    const [citations, setCitations] = useState<Citation[]>([])
    const [isQuerying, setIsQuerying] = useState(false)
    const [responseTime, setResponseTime] = useState<number | null>(null)
    const [tokensUsed, setTokensUsed] = useState<number | null>(null)
    const [copied, setCopied] = useState(false)

    const handleQuery = async () => {
        if (!query.trim()) {
            toast.error("Please enter a query")
            return
        }

        try {
            setIsQuerying(true)
            setAnswer("")
            setCitations([])

            const response = await playgroundApi.rag({
                query,
                kb_id: kbId,
                model,
                temperature,
                top_k: topK,
                system_prompt: systemPrompt,
            })

            setAnswer(response.answer)
            setCitations(response.citations)
            setResponseTime(response.response_time_ms)
            setTokensUsed(response.tokens_used)
            toast.success("Answer generated")
        } catch (error) {
            console.error(error)
            toast.error("Query failed")
        } finally {
            setIsQuerying(false)
        }
    }

    const handleCopy = () => {
        navigator.clipboard.writeText(answer)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
        toast.success("Answer copied to clipboard")
    }

    return (
        <div className="container mx-auto p-6 max-w-7xl">
            <div className="space-y-6">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold">RAG Playground</h1>
                    <p className="text-muted-foreground mt-1">
                        Test RAG queries with answer generation and citations
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Left Panel - Configuration */}
                    <div className="lg:col-span-1 space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle>Configuration</CardTitle>
                                <CardDescription>Model and query settings</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="kb-rag">Knowledge Base</Label>
                                    <Select value={kbId} onValueChange={setKbId}>
                                        <SelectTrigger id="kb-rag">
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
                                    <Label htmlFor="model">Model</Label>
                                    <Select value={model} onValueChange={setModel}>
                                        <SelectTrigger id="model">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="gpt-4">GPT-4</SelectItem>
                                            <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                                            <SelectItem value="claude-3-opus">Claude 3 Opus</SelectItem>
                                            <SelectItem value="claude-3-sonnet">Claude 3 Sonnet</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="temp">Temperature: {temperature.toFixed(2)}</Label>
                                    <Slider
                                        id="temp"
                                        min={0}
                                        max={2}
                                        step={0.1}
                                        value={[temperature]}
                                        onValueChange={([value]) => setTemperature(value)}
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="topk-rag">Context Chunks: {topK}</Label>
                                    <Slider
                                        id="topk-rag"
                                        min={1}
                                        max={20}
                                        step={1}
                                        value={[topK]}
                                        onValueChange={([value]) => setTopK(value)}
                                    />
                                </div>

                                <Separator />

                                <div className="space-y-2">
                                    <Label htmlFor="prompt">System Prompt</Label>
                                    <Textarea
                                        id="prompt"
                                        value={systemPrompt}
                                        onChange={(e) => setSystemPrompt(e.target.value)}
                                        rows={6}
                                        className="font-mono text-sm"
                                    />
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Right Panel - Query & Results */}
                    <div className="lg:col-span-2 space-y-6">
                        {/* Query Input */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Query</CardTitle>
                                <CardDescription>Enter your question</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <Textarea
                                    placeholder="What is vector search and how does it work?"
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    rows={3}
                                />
                                <Button onClick={handleQuery} disabled={isQuerying} className="w-full">
                                    {isQuerying ? (
                                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                    ) : (
                                        <MessageSquare className="h-4 w-4 mr-2" />
                                    )}
                                    Generate Answer
                                </Button>
                            </CardContent>
                        </Card>

                        {/* Answer */}
                        {answer && (
                            <Card>
                                <CardHeader>
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <CardTitle>Answer</CardTitle>
                                            <CardDescription>
                                                {responseTime}ms • {tokensUsed} tokens • {model}
                                            </CardDescription>
                                        </div>
                                        <Button variant="outline" size="sm" onClick={handleCopy}>
                                            {copied ? (
                                                <Check className="h-4 w-4" />
                                            ) : (
                                                <Copy className="h-4 w-4" />
                                            )}
                                        </Button>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <div className="prose prose-sm dark:prose-invert max-w-none">
                                        <p className="whitespace-pre-wrap leading-relaxed">{answer}</p>
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {/* Citations */}
                        {citations.length > 0 && (
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <BookOpen className="h-5 w-5" />
                                        Citations ({citations.length})
                                    </CardTitle>
                                    <CardDescription>Source documents used to generate the answer</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <ScrollArea className="h-[400px] pr-4">
                                        <div className="space-y-4">
                                            {citations.map((citation) => (
                                                <div
                                                    key={citation.index}
                                                    className="border rounded-lg p-4 space-y-2"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        <Badge variant="outline">[{citation.index}]</Badge>
                                                        <FileText className="h-4 w-4 text-muted-foreground" />
                                                        <span className="text-sm font-medium">
                                                            {citation.document_name}
                                                        </span>
                                                        <Badge variant="secondary" className="ml-auto">
                                                            {citation.score.toFixed(3)}
                                                        </Badge>
                                                    </div>
                                                    <p className="text-sm text-muted-foreground leading-relaxed">
                                                        {citation.chunk_content}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    </ScrollArea>
                                </CardContent>
                            </Card>
                        )}

                        {/* Empty State */}
                        {!isQuerying && !answer && (
                            <Card>
                                <CardContent className="flex flex-col items-center justify-center py-12">
                                    <MessageSquare className="h-12 w-12 text-muted-foreground mb-4" />
                                    <p className="text-muted-foreground text-center">
                                        Enter a query above to generate an answer
                                    </p>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
