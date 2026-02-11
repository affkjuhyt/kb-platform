"use client"

import { useState, useEffect } from "react"
import { FileEdit, Save, Loader2, Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { playgroundApi } from "@/lib/api/playground"
import { PromptTemplate, SavedPrompt } from "@/types/playground"
import { toast } from "sonner"

export default function PromptsPlaygroundPage() {
    const [templates, setTemplates] = useState<PromptTemplate[]>([])
    const [savedPrompts, setSavedPrompts] = useState<SavedPrompt[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)

    const [promptName, setPromptName] = useState("")
    const [promptContent, setPromptContent] = useState("")
    const [selectedKb, setSelectedKb] = useState<string | undefined>(undefined)
    const [selectedCategory, setSelectedCategory] = useState<string>("all")

    useEffect(() => {
        loadData()
    }, [])

    const loadData = async () => {
        try {
            setIsLoading(true)
            const [templatesData, savedData] = await Promise.all([
                playgroundApi.getTemplates(),
                playgroundApi.getSavedPrompts(),
            ])
            setTemplates(templatesData)
            setSavedPrompts(savedData)
        } catch (error) {
            console.error(error)
            toast.error("Failed to load prompts")
        } finally {
            setIsLoading(false)
        }
    }

    const handleSavePrompt = async () => {
        if (!promptName.trim() || !promptContent.trim()) {
            toast.error("Please provide a name and content for the prompt")
            return
        }

        try {
            setIsSaving(true)
            const saved = await playgroundApi.savePrompt({
                name: promptName,
                content: promptContent,
                kb_id: selectedKb,
            })
            setSavedPrompts([saved, ...savedPrompts])
            setPromptName("")
            setPromptContent("")
            toast.success("Prompt saved successfully")
        } catch (error) {
            console.error(error)
            toast.error("Failed to save prompt")
        } finally {
            setIsSaving(false)
        }
    }

    const handleLoadTemplate = (template: PromptTemplate) => {
        setPromptContent(template.content)
        toast.success(`Loaded template: ${template.name}`)
    }

    const handleLoadSaved = (saved: SavedPrompt) => {
        setPromptName(saved.name)
        setPromptContent(saved.content)
        setSelectedKb(saved.kb_id)
        toast.success(`Loaded prompt: ${saved.name}`)
    }

    const filteredTemplates = selectedCategory === "all"
        ? templates
        : templates.filter(t => t.category === selectedCategory)

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-full">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    return (
        <div className="container mx-auto p-6 max-w-7xl">
            <div className="space-y-6">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold">Prompt Editor</h1>
                    <p className="text-muted-foreground mt-1">
                        Create and manage system prompts for RAG queries
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Left Panel - Templates & Saved */}
                    <div className="lg:col-span-1 space-y-6">
                        <Tabs defaultValue="templates">
                            <TabsList className="grid w-full grid-cols-2">
                                <TabsTrigger value="templates">Templates</TabsTrigger>
                                <TabsTrigger value="saved">Saved</TabsTrigger>
                            </TabsList>

                            <TabsContent value="templates" className="mt-4">
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Prompt Templates</CardTitle>
                                        <CardDescription>Pre-built prompt templates</CardDescription>
                                        <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="all">All Categories</SelectItem>
                                                <SelectItem value="general">General</SelectItem>
                                                <SelectItem value="technical">Technical</SelectItem>
                                                <SelectItem value="creative">Creative</SelectItem>
                                                <SelectItem value="analytical">Analytical</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </CardHeader>
                                    <CardContent>
                                        <ScrollArea className="h-[500px] pr-4">
                                            <div className="space-y-3">
                                                {filteredTemplates.map((template) => (
                                                    <div
                                                        key={template.id}
                                                        className="border rounded-lg p-3 hover:bg-muted/50 transition-colors cursor-pointer"
                                                        onClick={() => handleLoadTemplate(template)}
                                                    >
                                                        <div className="flex items-start justify-between gap-2">
                                                            <div className="flex-1">
                                                                <h4 className="font-medium text-sm">{template.name}</h4>
                                                                <p className="text-xs text-muted-foreground mt-1">
                                                                    {template.description}
                                                                </p>
                                                            </div>
                                                            <Badge variant="outline" className="capitalize text-xs">
                                                                {template.category}
                                                            </Badge>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </ScrollArea>
                                    </CardContent>
                                </Card>
                            </TabsContent>

                            <TabsContent value="saved" className="mt-4">
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Saved Prompts</CardTitle>
                                        <CardDescription>Your custom prompts</CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <ScrollArea className="h-[500px] pr-4">
                                            {savedPrompts.length === 0 ? (
                                                <div className="text-center py-8 text-muted-foreground text-sm">
                                                    No saved prompts yet
                                                </div>
                                            ) : (
                                                <div className="space-y-3">
                                                    {savedPrompts.map((saved) => (
                                                        <div
                                                            key={saved.id}
                                                            className="border rounded-lg p-3 hover:bg-muted/50 transition-colors cursor-pointer"
                                                            onClick={() => handleLoadSaved(saved)}
                                                        >
                                                            <h4 className="font-medium text-sm">{saved.name}</h4>
                                                            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                                                {saved.content}
                                                            </p>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </ScrollArea>
                                    </CardContent>
                                </Card>
                            </TabsContent>
                        </Tabs>
                    </div>

                    {/* Right Panel - Editor */}
                    <div className="lg:col-span-2 space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle>Prompt Editor</CardTitle>
                                <CardDescription>Create or edit your system prompt</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="prompt-name">Prompt Name</Label>
                                        <Input
                                            id="prompt-name"
                                            placeholder="My Custom Prompt"
                                            value={promptName}
                                            onChange={(e) => setPromptName(e.target.value)}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="kb-select">Knowledge Base (Optional)</Label>
                                        <Select value={selectedKb} onValueChange={setSelectedKb}>
                                            <SelectTrigger id="kb-select">
                                                <SelectValue placeholder="None" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="none">None</SelectItem>
                                                <SelectItem value="kb-1">Product Documentation</SelectItem>
                                                <SelectItem value="kb-2">Technical Guides</SelectItem>
                                                <SelectItem value="kb-3">Customer Support</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="prompt-content">Prompt Content</Label>
                                    <Textarea
                                        id="prompt-content"
                                        placeholder="You are a helpful assistant..."
                                        value={promptContent}
                                        onChange={(e) => setPromptContent(e.target.value)}
                                        rows={15}
                                        className="font-mono text-sm"
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Use variables like {"{context}"} and {"{question}"} in your prompt
                                    </p>
                                </div>

                                <Separator />

                                <div className="flex gap-2">
                                    <Button onClick={handleSavePrompt} disabled={isSaving}>
                                        {isSaving ? (
                                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                        ) : (
                                            <Save className="h-4 w-4 mr-2" />
                                        )}
                                        Save Prompt
                                    </Button>
                                    <Button
                                        variant="outline"
                                        onClick={() => {
                                            setPromptName("")
                                            setPromptContent("")
                                            setSelectedKb(undefined)
                                        }}
                                    >
                                        <Plus className="h-4 w-4 mr-2" />
                                        New
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Preview */}
                        {promptContent && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>Preview</CardTitle>
                                    <CardDescription>How your prompt will appear</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="bg-muted rounded-lg p-4">
                                        <pre className="text-sm whitespace-pre-wrap font-mono">
                                            {promptContent}
                                        </pre>
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
