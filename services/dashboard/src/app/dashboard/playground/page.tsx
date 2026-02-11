"use client"

import Link from "next/link"
import {
    Search,
    MessageSquare,
    FileEdit,
    GitCompare,
    ArrowRight,
    Sparkles,
    Braces
} from "lucide-react"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"

const playgroundTools = [
    {
        name: "Semantic Search",
        description: "Test your knowledge base indexing and search quality with semantic and keyword queries.",
        href: "/dashboard/playground/search",
        icon: Search,
        color: "text-blue-500",
        bgColor: "bg-blue-500/10",
    },
    {
        name: "RAG Explorer",
        description: "Interactively test the full Retrieval-Augmented Generation pipeline with live data.",
        href: "/dashboard/playground/rag",
        icon: MessageSquare,
        color: "text-green-500",
        bgColor: "bg-green-500/10",
    },
    {
        name: "Prompt Studio",
        description: "Draft, test, and refine system prompts to optimize your LLM's performance.",
        href: "/dashboard/playground/prompts",
        icon: FileEdit,
        color: "text-purple-500",
        bgColor: "bg-purple-500/10",
    },
    {
        name: "Model Comparison",
        description: "Compare outputs from multiple models side-by-side using the same context and query.",
        href: "/dashboard/playground/compare",
        icon: GitCompare,
        color: "text-orange-500",
        bgColor: "bg-orange-500/10",
    },
    {
        name: "Data Extraction",
        description: "Extract structured data from unstructured text using JSON schemas.",
        href: "/dashboard/playground/extraction",
        icon: Braces,
        color: "text-pink-500",
        bgColor: "bg-pink-500/10",
    },
]

export default function PlaygroundPage() {
    return (
        <div className="container mx-auto px-6 py-10 space-y-12">
            <div className="max-w-3xl">
                <div className="flex items-center gap-2 mb-4">
                    <Sparkles className="h-5 w-5 text-primary animate-pulse" />
                    <span className="text-sm font-semibold tracking-wider uppercase text-primary">Lab Environment</span>
                </div>
                <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl mb-4">
                    Playground
                </h1>
                <p className="text-xl text-muted-foreground leading-relaxed">
                    Experiment with your knowledge bases using our suite of testing and optimization tools.
                    Fine-tune search quality, test RAG pipelines, and compare model performance in real-time.
                </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {playgroundTools.map((tool) => {
                    const Icon = tool.icon
                    return (
                        <Card key={tool.name} className="group overflow-hidden transition-all hover:shadow-md border-muted-foreground/10">
                            <CardHeader className="flex flex-row items-center gap-4 space-y-0">
                                <div className={`p-3 rounded-xl ${tool.bgColor} ${tool.color} transition-transform group-hover:scale-110`}>
                                    <Icon className="h-6 w-6" />
                                </div>
                                <div className="space-y-1">
                                    <CardTitle>{tool.name}</CardTitle>
                                    <CardDescription>{tool.name === "RAG Explorer" ? "Retrieval-Augmented Generation" : "Optimization Tool"}</CardDescription>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <p className="text-muted-foreground leading-relaxed">
                                    {tool.description}
                                </p>
                                <Button asChild variant="ghost" className="group/btn p-0 hover:bg-transparent text-primary font-semibold">
                                    <Link href={tool.href} className="flex items-center gap-2">
                                        Open Tool
                                        <ArrowRight className="h-4 w-4 transition-transform group-hover/btn:translate-x-1" />
                                    </Link>
                                </Button>
                            </CardContent>
                        </Card>
                    )
                })}
            </div>

            <div className="bg-muted/30 rounded-2xl p-8 border border-dashed border-muted-foreground/20 text-center">
                <h3 className="text-lg font-semibold mb-2">Need help getting started?</h3>
                <p className="text-muted-foreground mb-6 max-w-lg mx-auto">
                    Check out our documentation for best practices on prompt engineering,
                    knowledge base optimization, and performance evaluation.
                </p>
                <div className="flex justify-center gap-4">
                    <Button variant="outline" size="sm">Documentation</Button>
                    <Button variant="outline" size="sm">Tutorial Videos</Button>
                </div>
            </div>
        </div>
    )
}
