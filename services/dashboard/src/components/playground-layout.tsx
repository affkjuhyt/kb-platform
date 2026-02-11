"use client"

import { ReactNode } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Search, MessageSquare, FileEdit, GitCompare } from "lucide-react"

interface PlaygroundLayoutProps {
    children: ReactNode
}

const playgroundTabs = [
    {
        name: "Search",
        href: "/dashboard/playground/search",
        icon: Search,
        description: "Test search queries and view results",
    },
    {
        name: "RAG",
        href: "/dashboard/playground/rag",
        icon: MessageSquare,
        description: "Query with answer generation",
    },
    {
        name: "Prompts",
        href: "/dashboard/playground/prompts",
        icon: FileEdit,
        description: "Customize system prompts",
    },
    {
        name: "Compare",
        href: "/dashboard/playground/compare",
        icon: GitCompare,
        description: "Compare model outputs",
    },
]

export function PlaygroundLayout({ children }: PlaygroundLayoutProps) {
    const pathname = usePathname()

    return (
        <div className="flex flex-col h-full">
            {/* Navigation Tabs */}
            <div className="border-b bg-background">
                <div className="container mx-auto px-6">
                    <nav className="flex gap-6" aria-label="Playground tabs">
                        {playgroundTabs.map((tab) => {
                            const isActive = pathname === tab.href
                            const Icon = tab.icon

                            return (
                                <Link
                                    key={tab.href}
                                    href={tab.href}
                                    className={cn(
                                        "flex items-center gap-2 px-3 py-4 border-b-2 text-sm font-medium transition-colors",
                                        isActive
                                            ? "border-primary text-foreground"
                                            : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/50"
                                    )}
                                >
                                    <Icon className="h-4 w-4" />
                                    {tab.name}
                                </Link>
                            )
                        })}
                    </nav>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto">
                {children}
            </div>
        </div>
    )
}
