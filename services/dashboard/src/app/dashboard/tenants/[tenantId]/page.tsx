"use client"

import { useEffect, useState } from "react"
import { useTenant } from "@/context/tenant-context"
import { Tenant, TenantSettings, TenantUser } from "@/types/tenant"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, Save, Trash2, UserPlus } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { toast } from "sonner"
import { tenantApi } from "@/lib/api/tenants"
import { useRouter } from "next/navigation"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"

export default function TenantDetailsPage({ params }: { params: { tenantId: string } }) {
    const { tenantId } = params
    const { currentTenant, refreshTenants } = useTenant()
    const router = useRouter()

    const [tenant, setTenant] = useState<Tenant | null>(null)
    const [settings, setSettings] = useState<TenantSettings | null>(null)
    const [users, setUsers] = useState<TenantUser[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)

    // Invite User State
    const [isInviteOpen, setIsInviteOpen] = useState(false)
    const [inviteEmail, setInviteEmail] = useState("")
    const [inviteRole, setInviteRole] = useState("member")
    const [isInviting, setIsInviting] = useState(false)

    // Fetch Data
    useEffect(() => {
        const loadData = async () => {
            try {
                setIsLoading(true)
                const [tenantData, settingsData, usersData] = await Promise.all([
                    tenantApi.get(tenantId),
                    tenantApi.getSettings(tenantId),
                    tenantApi.listUsers(tenantId)
                ])
                setTenant(tenantData)
                setSettings(settingsData)
                setUsers(usersData)
            } catch (error) {
                console.error(error)
                toast.error("Failed to load tenant data")
            } finally {
                setIsLoading(false)
            }
        }
        loadData()
    }, [tenantId])

    const handleUpdateTenant = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!tenant) return

        try {
            setIsSaving(true)
            await tenantApi.update(tenant.id, {
                name: tenant.name,
                description: tenant.description,
                plan: tenant.plan
            })
            toast.success("Tenant updated successfully")
            refreshTenants()
        } catch (error) {
            console.error(error)
            toast.error("Failed to update tenant")
        } finally {
            setIsSaving(false)
        }
    }

    const handleUpdateSettings = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!settings || !tenant) return

        try {
            setIsSaving(true)
            await tenantApi.updateSettings(tenant.id, {
                rate_limit: settings.rate_limit,
                quotas: settings.quotas,
                api_keys_enabled: settings.api_keys_enabled
            })
            toast.success("Settings updated successfully")
        } catch (error) {
            console.error(error)
            toast.error("Failed to update settings")
        } finally {
            setIsSaving(false)
        }
    }

    const handleInviteUser = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!tenant || !inviteEmail) return

        try {
            setIsInviting(true)
            await tenantApi.inviteUser(tenant.id, {
                email: inviteEmail,
                role: inviteRole as any
            })
            toast.success("User invited successfully")
            setInviteEmail("")
            setIsInviteOpen(false)
            // Refresh user list
            const updatedUsers = await tenantApi.listUsers(tenant.id)
            setUsers(updatedUsers)
        } catch (error) {
            console.error(error)
            toast.error("Failed to invite user")
        } finally {
            setIsInviting(false)
        }
    }

    const handleRemoveUser = async (userId: string) => {
        if (!tenant || !confirm("Are you sure you want to remove this user?")) return

        try {
            await tenantApi.removeUser(tenant.id, userId)
            toast.success("User removed successfully")
            setUsers(users.filter(u => u.user_id !== userId))
        } catch (error) {
            console.error(error)
            toast.error("Failed to remove user")
        }
    }

    if (isLoading) {
        return (
            <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    if (!tenant || !settings) {
        return <div>Tenant not found</div>
    }

    return (
        <div className="flex-1 space-y-4 p-8 pt-6">
            <div className="flex items-center justify-between space-y-2">
                <h2 className="text-3xl font-bold tracking-tight">Tenant Settings</h2>
                <div className="flex items-center space-x-2">
                    <Button variant="outline" onClick={() => router.push("/dashboard/tenants")}>
                        Back to List
                    </Button>
                </div>
            </div>

            <Tabs defaultValue="overview" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="settings">Settings & Quotas</TabsTrigger>
                    <TabsTrigger value="users">Users</TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-4">
                    <div className="rounded-xl border bg-card text-card-foreground shadow max-w-2xl p-6">
                        <form onSubmit={handleUpdateTenant} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="name">Tenant Name</Label>
                                <Input
                                    id="name"
                                    value={tenant.name}
                                    onChange={(e) => setTenant({ ...tenant, name: e.target.value })}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="description">Description</Label>
                                <Input
                                    id="description"
                                    value={tenant.description || ""}
                                    onChange={(e) => setTenant({ ...tenant, description: e.target.value })}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="plan">Subscription Plan</Label>
                                <select
                                    id="plan"
                                    value={tenant.plan}
                                    onChange={(e) => setTenant({ ...tenant, plan: e.target.value })}
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    <option value="free">Free</option>
                                    <option value="pro">Pro</option>
                                    <option value="enterprise">Enterprise</option>
                                </select>
                            </div>
                            <Button type="submit" disabled={isSaving}>
                                {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                <Save className="mr-2 h-4 w-4" /> Save Changes
                            </Button>
                        </form>
                    </div>
                </TabsContent>

                <TabsContent value="settings" className="space-y-4">
                    <div className="rounded-xl border bg-card text-card-foreground shadow max-w-2xl p-6">
                        <form onSubmit={handleUpdateSettings} className="space-y-6">

                            <div className="space-y-4">
                                <h3 className="text-lg font-medium">Rate Limits</h3>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Requests per Minute</Label>
                                        <Input
                                            type="number"
                                            value={settings.rate_limit.requests_per_minute}
                                            onChange={(e) => setSettings({
                                                ...settings,
                                                rate_limit: { ...settings.rate_limit, requests_per_minute: parseInt(e.target.value) }
                                            })}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Requests per Day</Label>
                                        <Input
                                            type="number"
                                            value={settings.rate_limit.requests_per_day}
                                            onChange={(e) => setSettings({
                                                ...settings,
                                                rate_limit: { ...settings.rate_limit, requests_per_day: parseInt(e.target.value) }
                                            })}
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-lg font-medium">Quotas</h3>
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="space-y-2">
                                        <Label>Max Users</Label>
                                        <Input
                                            type="number"
                                            value={settings.quotas.max_users}
                                            onChange={(e) => setSettings({
                                                ...settings,
                                                quotas: { ...settings.quotas, max_users: parseInt(e.target.value) }
                                            })}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Max Docs</Label>
                                        <Input
                                            type="number"
                                            value={settings.quotas.max_documents}
                                            onChange={(e) => setSettings({
                                                ...settings,
                                                quotas: { ...settings.quotas, max_documents: parseInt(e.target.value) }
                                            })}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Max Storage (GB)</Label>
                                        <Input
                                            type="number"
                                            value={settings.quotas.max_storage_gb}
                                            onChange={(e) => setSettings({
                                                ...settings,
                                                quotas: { ...settings.quotas, max_storage_gb: parseInt(e.target.value) }
                                            })}
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center space-x-2">
                                <Switch
                                    id="api-keys"
                                    checked={settings.api_keys_enabled}
                                    onCheckedChange={(checked) => setSettings({ ...settings, api_keys_enabled: checked })}
                                />
                                <Label htmlFor="api-keys">Enable API Keys</Label>
                            </div>

                            <Button type="submit" disabled={isSaving}>
                                {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                <Save className="mr-2 h-4 w-4" /> Save Settings
                            </Button>
                        </form>
                    </div>
                </TabsContent>

                <TabsContent value="users" className="space-y-4">
                    <div className="flex justify-between">
                        <h3 className="text-lg font-medium">Team Members</h3>
                        <Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}>
                            <DialogTrigger asChild>
                                <Button variant="outline">
                                    <UserPlus className="mr-2 h-4 w-4" /> Invite User
                                </Button>
                            </DialogTrigger>
                            <DialogContent>
                                <DialogHeader>
                                    <DialogTitle>Invite User</DialogTitle>
                                </DialogHeader>
                                <form onSubmit={handleInviteUser} className="space-y-4">
                                    <div className="space-y-2">
                                        <Label>Email Address</Label>
                                        <Input
                                            type="email"
                                            placeholder="user@example.com"
                                            value={inviteEmail}
                                            onChange={(e) => setInviteEmail(e.target.value)}
                                            required
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Role</Label>
                                        <select
                                            value={inviteRole}
                                            onChange={(e) => setInviteRole(e.target.value)}
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                            <option value="member">Member</option>
                                            <option value="admin">Admin</option>
                                            <option value="viewer">Viewer</option>
                                            <option value="owner">Owner</option>
                                        </select>
                                    </div>
                                    <DialogFooter>
                                        <Button type="submit" disabled={isInviting}>
                                            {isInviting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                            Send Invitation
                                        </Button>
                                    </DialogFooter>
                                </form>
                            </DialogContent>
                        </Dialog>
                    </div>

                    <div className="rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Name/Email</TableHead>
                                    <TableHead>Role</TableHead>
                                    <TableHead>Joined At</TableHead>
                                    <TableHead className="w-[100px]">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {users.map((user) => (
                                    <TableRow key={user.user_id}>
                                        <TableCell>
                                            <div className="font-medium">{user.name}</div>
                                            <div className="text-sm text-muted-foreground">{user.email}</div>
                                        </TableCell>
                                        <TableCell>
                                            <span className="capitalize badge">{user.role}</span>
                                        </TableCell>
                                        <TableCell>
                                            {new Date(user.joined_at).toLocaleDateString()}
                                        </TableCell>
                                        <TableCell>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => handleRemoveUser(user.user_id)}
                                                className="text-destructive hover:text-destructive"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    )
}
