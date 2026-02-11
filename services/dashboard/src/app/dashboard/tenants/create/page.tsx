"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
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
import { Input } from "@/components/ui/input"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import { tenantApi } from "@/lib/api/tenants"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Building, ArrowLeft } from "lucide-react"
import { useAuth } from "@/context/auth-context"

const formSchema = z.object({
    name: z.string().min(2, {
        message: "Workspace name must be at least 2 characters.",
    }),
    description: z.string().optional(),
    plan: z.string().default("free"),
})

export default function CreateTenantPage() {
    const router = useRouter()
    const { user } = useAuth()
    const [loading, setLoading] = useState(false)

    const form = useForm({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            description: "",
            plan: "free",
        },
    })

    async function onSubmit(values: z.infer<typeof formSchema>) {
        if (!user) {
            toast.error("You must be logged in to create a workspace")
            return
        }

        setLoading(true)
        try {
            await tenantApi.create({
                name: values.name,
                description: values.description,
                plan: values.plan,
            })
            toast.success("Workspace created successfully!")
            router.push("/dashboard/tenants")
        } catch (error: unknown) {
            console.error("Failed to create workspace:", error)
            toast.error("Failed to create workspace. Please try again.")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="container max-w-2xl py-10">
            <div className="mb-8">
                <Button
                    variant="ghost"
                    className="pl-0 hover:bg-transparent hover:text-primary"
                    onClick={() => router.back()}
                >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2 mb-2">
                        <div className="p-2 bg-primary/10 rounded-lg">
                            <Building className="h-6 w-6 text-primary" />
                        </div>
                        <CardTitle className="text-2xl">Create New Workspace</CardTitle>
                    </div>
                    <CardDescription>
                        Create a dedicated workspace for your team. Each workspace has its own documents, knowledge bases, and settings.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                            <FormField
                                control={form.control}
                                name="name"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Workspace Name</FormLabel>
                                        <FormControl>
                                            <Input placeholder="Acme Corp" {...field} />
                                        </FormControl>
                                        <FormDescription>
                                            This is your public display name.
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="description"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Description (Optional)</FormLabel>
                                        <FormControl>
                                            <Input placeholder="Team workspace for project X" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="plan"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Plan</FormLabel>
                                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select a plan" />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                <SelectItem value="free">Free (Starter)</SelectItem>
                                                <SelectItem value="pro">Pro (Scalable)</SelectItem>
                                                <SelectItem value="enterprise">Enterprise (Custom)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormDescription>
                                            Different plans have different quotas for documents and API usage.
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <Button type="submit" className="w-full" disabled={loading}>
                                {loading ? "Creating Dashboard..." : "Create Workspace"}
                            </Button>
                        </form>
                    </Form>
                </CardContent>
            </Card>
        </div>
    )
}
