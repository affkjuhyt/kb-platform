"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { toast } from "sonner"
import axios from "axios"
import { ArrowLeft, Braces, Play } from "lucide-react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/context/auth-context"

const formSchema = z.object({
    query: z.string().min(1, "Text to extract from is required"),
    schema_name: z.string().min(1, "Schema name is required"),
    schema_definition: z.string().min(1, "Schema definition (JSON) is required").refine((val) => {
        try {
            JSON.parse(val)
            return true
        } catch {
            return false
        }
    }, "Invalid JSON schema"),
})

export interface ExtractionResult {
    success: boolean
    data: unknown
    confidence: number
    validation_errors?: string[]
}

export default function ExtractionPlaygroundPage() {
    const router = useRouter()
    const { user } = useAuth()
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<ExtractionResult | null>(null)

    const form = useForm({
        resolver: zodResolver(formSchema),
        defaultValues: {
            query: "Alice lives in Wonderland and is 10 years old. Bob is 12 and lives in Builderland.",
            schema_name: "people_extraction",
            schema_definition: JSON.stringify({
                type: "object",
                properties: {
                    people: {
                        type: "array",
                        items: {
                            type: "object",
                            properties: {
                                name: { type: "string" },
                                age: { type: "integer" },
                                location: { type: "string" }
                            },
                            required: ["name", "age"]
                        }
                    }
                }
            }, null, 2),
        },
    })

    async function onSubmit(values: z.infer<typeof formSchema>) {
        if (!user) return

        setLoading(true)
        setResult(null)
        try {
            const schema = JSON.parse(values.schema_definition)

            // Call the extract endpoint
            // Note: The backend expects 'schema' in the payload, not 'schema_definition'
            const response = await axios.post("/api/query/extract", {
                query: values.query,
                schema: schema,
                schema_name: values.schema_name,
                tenant_id: user.tenant_id,
            })

            setResult(response.data)
            toast.success("Extraction completed")
        } catch (error: unknown) {
            console.error("Extraction error:", error)
            if (axios.isAxiosError(error)) {
                toast.error(error.response?.data?.detail || "Extraction failed")
            } else {
                toast.error("Extraction failed")
            }
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="container py-8 space-y-8">
            <div className="flex items-center gap-4">
                <Button
                    variant="ghost"
                    className="pl-0 hover:bg-transparent hover:text-primary"
                    onClick={() => router.back()}
                >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                </Button>
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Extraction Playground</h2>
                    <p className="text-muted-foreground">
                        Test structured data extraction from text using JSON schemas.
                    </p>
                </div>
            </div>

            <div className="grid gap-8 md:grid-cols-2">
                <Card className="md:row-span-2">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Braces className="h-5 w-5" />
                            Configuration
                        </CardTitle>
                        <CardDescription>
                            Define your input text and target schema
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                                <FormField
                                    control={form.control}
                                    name="query"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Input Text (or Search Query)</FormLabel>
                                            <FormControl>
                                                <Textarea
                                                    placeholder="Paste text here..."
                                                    className="min-h-[150px] font-mono text-sm"
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormDescription>
                                                The text content or query to extract data from.
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <div className="grid grid-cols-2 gap-4">
                                    <FormField
                                        control={form.control}
                                        name="schema_name"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Schema Name</FormLabel>
                                                <FormControl>
                                                    <Input placeholder="my_schema" {...field} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </div>

                                <FormField
                                    control={form.control}
                                    name="schema_definition"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>JSON Schema</FormLabel>
                                            <FormControl>
                                                <Textarea
                                                    placeholder="{ ... }"
                                                    className="min-h-[300px] font-mono text-sm"
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormDescription>
                                                Define the structure you want to extract using standard JSON Schema.
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <Button type="submit" className="w-full" disabled={loading}>
                                    {loading ? (
                                        <>Extracting...</>
                                    ) : (
                                        <>
                                            <Play className="mr-2 h-4 w-4" /> Run Extraction
                                        </>
                                    )}
                                </Button>
                            </form>
                        </Form>
                    </CardContent>
                </Card>

                <Card className="h-full">
                    <CardHeader>
                        <CardTitle>Results</CardTitle>
                        <CardDescription>
                            Extracted structured data
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {result ? (
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                                    <span className={result.success ? "text-green-500" : "text-red-500"}>
                                        {result.success ? "Success" : "Failed"}
                                    </span>
                                    <span>•</span>
                                    <span>Confidence: {(result.confidence * 100).toFixed(1)}%</span>
                                </div>
                                <div className="bg-muted p-4 rounded-lg overflow-auto max-h-[600px]">
                                    <pre className="text-sm font-mono">
                                        {JSON.stringify(result.data, null, 2)}
                                    </pre>
                                </div>
                                {result.validation_errors && result.validation_errors.length > 0 && (
                                    <div className="bg-destructive/10 text-destructive p-4 rounded-lg text-sm">
                                        <p className="font-semibold mb-1">Validation Errors:</p>
                                        <ul className="list-disc pl-5">
                                            {result.validation_errors.map((err: string, i: number) => (
                                                <li key={i}>{err}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="h-[400px] flex items-center justify-center text-muted-foreground border-2 border-dashed rounded-lg">
                                Run extraction to see results
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
