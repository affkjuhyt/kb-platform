"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/context/auth-context"
import {
    User,
    Settings,
    Key,
    Info,
    Copy,
    Check,
    RefreshCw,
    Moon,
    Sun,
    Monitor,
    Bell,
    Globe,
    Loader2,
    Activity
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { AuditLogsTable } from "@/components/audit-logs-table"
import axios from "axios"
import { Label } from "@/components/ui/label"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from "@/components/ui/tabs"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { toast } from "sonner"
import { kbApi } from "@/lib/api/knowledge-base"
import { KnowledgeBase } from "@/types/knowledge-base"

// Preferences stored in localStorage
interface UserPreferences {
    theme: "light" | "dark" | "system"
    language: "en" | "vi"
    emailNotifications: boolean
    displayDensity: "comfortable" | "compact"
}

const DEFAULT_PREFERENCES: UserPreferences = {
    theme: "system",
    language: "en",
    emailNotifications: true,
    displayDensity: "comfortable",
}

export default function SettingsPage() {
    const { user } = useAuth()

    // Profile state
    const [currentPassword, setCurrentPassword] = useState("")
    const [newPassword, setNewPassword] = useState("")
    const [confirmPassword, setConfirmPassword] = useState("")

    // Preferences state
    const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES)

    // API Key state
    const [apiKey, setApiKey] = useState<string>("")
    const [showRegenerateDialog, setShowRegenerateDialog] = useState(false)
    const [copied, setCopied] = useState(false)

    // System state
    const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
    const [isLoadingKBs, setIsLoadingKBs] = useState(true)

    // Load preferences from localStorage
    useEffect(() => {
        const stored = localStorage.getItem("userPreferences")
        if (stored) {
            try {
                setPreferences(JSON.parse(stored))
            } catch {
                setPreferences(DEFAULT_PREFERENCES)
            }
        }

        // Load API key from localStorage (mock)
        const storedKey = localStorage.getItem("apiKey")
        if (!storedKey) {
            const newKey = generateAPIKey()
            localStorage.setItem("apiKey", newKey)
            setApiKey(newKey)
        } else {
            setApiKey(storedKey)
        }
    }, [])

    // Load KB stats
    useEffect(() => {
        const loadKBs = async () => {
            try {
                setIsLoadingKBs(true)
                const kbs = await kbApi.list()
                setKnowledgeBases(kbs)
            } catch (error) {
                console.error("Failed to load KBs:", error)
            } finally {
                setIsLoadingKBs(false)
            }
        }
        loadKBs()
    }, [])

    // Save preferences to localStorage
    const savePreference = <K extends keyof UserPreferences>(
        key: K,
        value: UserPreferences[K]
    ) => {
        const updated = { ...preferences, [key]: value }
        setPreferences(updated)
        localStorage.setItem("userPreferences", JSON.stringify(updated))
        toast.success("Preference saved")
    }

    // Password change handler
    const handlePasswordChange = () => {
        if (!currentPassword || !newPassword || !confirmPassword) {
            toast.error("Please fill in all password fields")
            return
        }
        if (newPassword !== confirmPassword) {
            toast.error("New passwords do not match")
            return
        }
        if (newPassword.length < 8) {
            toast.error("Password must be at least 8 characters")
            return
        }

        // Mock password change (would call backend in production)
        toast.success("Password changed successfully")
        setCurrentPassword("")
        setNewPassword("")
        setConfirmPassword("")
    }

    // Generate random API key
    const generateAPIKey = () => {
        const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        let key = "nex_"
        for (let i = 0; i < 32; i++) {
            key += chars.charAt(Math.floor(Math.random() * chars.length))
        }
        return key
    }

    // Regenerate API key
    const handleRegenerateKey = async () => {
        try {
            const response = await axios.post("/auth/api-keys", {
                name: "Dashboard Key",
                permissions: ["read", "write"]
            })
            const newKey = response.data.api_key
            localStorage.setItem("apiKey", newKey)
            setApiKey(newKey)
            setShowRegenerateDialog(false)
            toast.success("API key regenerated successfully")
        } catch (error) {
            console.error("Failed to regenerate API key:", error)
            toast.error("Failed to regenerate API key")
        }
    }

    // Copy API key to clipboard
    const handleCopyKey = () => {
        navigator.clipboard.writeText(apiKey)
        setCopied(true)
        toast.success("API key copied to clipboard")
        setTimeout(() => setCopied(false), 2000)
    }

    // Mask API key for display
    const maskAPIKey = (key: string) => {
        if (!key) return ""
        if (key.length < 12) return key
        return key.substring(0, 8) + "•".repeat(20) + key.substring(key.length - 4)
    }

    // Calculate total stats
    const totalDocs = knowledgeBases.reduce((sum, kb) => sum + kb.document_count, 0)
    const totalChunks = knowledgeBases.reduce((sum, kb) => sum + kb.chunk_count, 0)

    return (
        <div className="container mx-auto px-6 py-10 max-w-6xl space-y-8">
            <div>
                <h1 className="text-4xl font-bold tracking-tight">Settings</h1>
                <p className="text-muted-foreground mt-2">
                    Manage your account settings and preferences
                </p>
            </div>

            <Tabs defaultValue="profile" className="space-y-6">
                <TabsList className="grid w-full grid-cols-4 lg:grid-cols-5">
                    <TabsTrigger value="profile">
                        <User className="h-4 w-4 mr-2" />
                        Profile
                    </TabsTrigger>
                    <TabsTrigger value="preferences">
                        <Settings className="h-4 w-4 mr-2" />
                        Preferences
                    </TabsTrigger>
                    <TabsTrigger value="api-keys">
                        <Key className="h-4 w-4 mr-2" />
                        API Keys
                    </TabsTrigger>
                    <TabsTrigger value="system">
                        <Info className="h-4 w-4 mr-2" />
                        System
                    </TabsTrigger>
                    <TabsTrigger value="audit">
                        <Activity className="h-4 w-4 mr-2" />
                        Audit Logs
                    </TabsTrigger>
                </TabsList>

                {/* Profile Tab */}
                <TabsContent value="profile" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Account Information</CardTitle>
                            <CardDescription>
                                Your account details and authentication settings
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid gap-4 md:grid-cols-2">
                                <div className="space-y-2">
                                    <Label>User ID</Label>
                                    <Input value={user?.id || ""} disabled />
                                </div>
                                <div className="space-y-2">
                                    <Label>Email Address</Label>
                                    <Input value={user?.email || ""} disabled />
                                </div>
                                <div className="space-y-2">
                                    <Label>Role</Label>
                                    <div className="flex items-center gap-2">
                                        <Input value={user?.role || ""} disabled className="flex-1" />
                                        <Badge variant="outline" className="capitalize">
                                            {user?.role}
                                        </Badge>
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <Label>Tenant ID</Label>
                                    <Input value={user?.tenant_id || ""} disabled />
                                </div>
                            </div>

                            <Separator />

                            <div>
                                <h3 className="text-lg font-semibold mb-4">Change Password</h3>
                                <div className="space-y-4 max-w-md">
                                    <div className="space-y-2">
                                        <Label htmlFor="current-password">Current Password</Label>
                                        <Input
                                            id="current-password"
                                            type="password"
                                            value={currentPassword}
                                            onChange={(e) => setCurrentPassword(e.target.value)}
                                            placeholder="Enter current password"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="new-password">New Password</Label>
                                        <Input
                                            id="new-password"
                                            type="password"
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            placeholder="Enter new password"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="confirm-password">Confirm New Password</Label>
                                        <Input
                                            id="confirm-password"
                                            type="password"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            placeholder="Confirm new password"
                                        />
                                    </div>
                                    <Button onClick={handlePasswordChange}>
                                        Update Password
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Preferences Tab */}
                <TabsContent value="preferences" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Appearance</CardTitle>
                            <CardDescription>
                                Customize the look and feel of the application
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label>Theme</Label>
                                    <p className="text-sm text-muted-foreground">
                                        Select your preferred color scheme
                                    </p>
                                </div>
                                <Select
                                    value={preferences.theme}
                                    onValueChange={(value: "light" | "dark" | "system") =>
                                        savePreference("theme", value)
                                    }
                                >
                                    <SelectTrigger className="w-[180px]">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="light">
                                            <div className="flex items-center gap-2">
                                                <Sun className="h-4 w-4" />
                                                Light
                                            </div>
                                        </SelectItem>
                                        <SelectItem value="dark">
                                            <div className="flex items-center gap-2">
                                                <Moon className="h-4 w-4" />
                                                Dark
                                            </div>
                                        </SelectItem>
                                        <SelectItem value="system">
                                            <div className="flex items-center gap-2">
                                                <Monitor className="h-4 w-4" />
                                                System
                                            </div>
                                        </SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <Separator />

                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label>Display Density</Label>
                                    <p className="text-sm text-muted-foreground">
                                        Adjust the spacing and size of UI elements
                                    </p>
                                </div>
                                <Select
                                    value={preferences.displayDensity}
                                    onValueChange={(value: "comfortable" | "compact") =>
                                        savePreference("displayDensity", value)
                                    }
                                >
                                    <SelectTrigger className="w-[180px]">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="comfortable">Comfortable</SelectItem>
                                        <SelectItem value="compact">Compact</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Localization</CardTitle>
                            <CardDescription>
                                Language and regional preferences
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label>Language</Label>
                                    <p className="text-sm text-muted-foreground">
                                        Select your preferred language
                                    </p>
                                </div>
                                <Select
                                    value={preferences.language}
                                    onValueChange={(value: "en" | "vi") =>
                                        savePreference("language", value)
                                    }
                                >
                                    <SelectTrigger className="w-[180px]">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="en">
                                            <div className="flex items-center gap-2">
                                                <Globe className="h-4 w-4" />
                                                English
                                            </div>
                                        </SelectItem>
                                        <SelectItem value="vi">
                                            <div className="flex items-center gap-2">
                                                <Globe className="h-4 w-4" />
                                                Tiếng Việt
                                            </div>
                                        </SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Notifications</CardTitle>
                            <CardDescription>
                                Manage how you receive notifications
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label>Email Notifications</Label>
                                    <p className="text-sm text-muted-foreground">
                                        Receive email updates about your account activity
                                    </p>
                                </div>
                                <Switch
                                    checked={preferences.emailNotifications}
                                    onCheckedChange={(checked) =>
                                        savePreference("emailNotifications", checked)
                                    }
                                />
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* API Keys Tab */}
                <TabsContent value="api-keys" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>API Key Management</CardTitle>
                            <CardDescription>
                                Manage your API keys for programmatic access
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="space-y-4">
                                <div>
                                    <Label>Your API Key</Label>
                                    <p className="text-sm text-muted-foreground mb-3">
                                        Use this key to authenticate API requests. Keep it secure and never share it publicly.
                                    </p>
                                    <div className="flex gap-2">
                                        <Input
                                            value={maskAPIKey(apiKey)}
                                            readOnly
                                            className="font-mono text-sm"
                                        />
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            onClick={handleCopyKey}
                                        >
                                            {copied ? (
                                                <Check className="h-4 w-4 text-green-500" />
                                            ) : (
                                                <Copy className="h-4 w-4" />
                                            )}
                                        </Button>
                                    </div>
                                </div>

                                <div className="flex gap-2">
                                    <Button
                                        variant="destructive"
                                        onClick={() => setShowRegenerateDialog(true)}
                                    >
                                        <RefreshCw className="h-4 w-4 mr-2" />
                                        Regenerate Key
                                    </Button>
                                </div>

                                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
                                    <div className="flex gap-3">
                                        <Bell className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                                        <div className="space-y-1">
                                            <p className="text-sm font-medium">Security Notice</p>
                                            <p className="text-sm text-muted-foreground">
                                                Regenerating your API key will immediately invalidate the current key.
                                                Any applications using the old key will need to be updated.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* System Tab */}
                <TabsContent value="system" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Tenant Information</CardTitle>
                            <CardDescription>
                                Details about your organization and usage
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid gap-4 md:grid-cols-2">
                                <div className="space-y-1">
                                    <p className="text-sm text-muted-foreground">Tenant ID</p>
                                    <p className="font-medium font-mono text-sm">{user?.tenant_id}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-sm text-muted-foreground">User Role</p>
                                    <Badge variant="outline" className="capitalize">
                                        {user?.role}
                                    </Badge>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Knowledge Base Statistics</CardTitle>
                            <CardDescription>
                                Overview of your knowledge bases and storage
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {isLoadingKBs ? (
                                <div className="flex items-center justify-center py-8">
                                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    <div className="grid gap-4 md:grid-cols-3">
                                        <div className="space-y-1">
                                            <p className="text-sm text-muted-foreground">Total Knowledge Bases</p>
                                            <p className="text-2xl font-bold">{knowledgeBases.length}</p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-sm text-muted-foreground">Total Documents</p>
                                            <p className="text-2xl font-bold">{totalDocs}</p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-sm text-muted-foreground">Total Chunks</p>
                                            <p className="text-2xl font-bold">{totalChunks.toLocaleString()}</p>
                                        </div>
                                    </div>

                                    {knowledgeBases.length > 0 && (
                                        <>
                                            <Separator />
                                            <div className="space-y-2">
                                                <p className="text-sm font-medium">Knowledge Bases</p>
                                                <div className="space-y-2">
                                                    {knowledgeBases.map((kb) => (
                                                        <div
                                                            key={kb.id}
                                                            className="flex items-center justify-between p-3 border rounded-lg"
                                                        >
                                                            <div>
                                                                <p className="font-medium">{kb.name}</p>
                                                                <p className="text-xs text-muted-foreground">
                                                                    Model: {kb.embedding_model}
                                                                </p>
                                                            </div>
                                                            <div className="text-right text-sm text-muted-foreground">
                                                                <p>{kb.document_count} docs</p>
                                                                <p>{kb.chunk_count.toLocaleString()} chunks</p>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Audit Logs Tab */}
                <TabsContent value="audit">
                    <AuditLogsTable />
                </TabsContent>
            </Tabs>

            {/* Regenerate API Key Confirmation Dialog */}
            <Dialog open={showRegenerateDialog} onOpenChange={setShowRegenerateDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Regenerate API Key?</DialogTitle>
                        <DialogDescription>
                            This will create a new API key and immediately invalidate your current key.
                            Any applications using the old key will stop working.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setShowRegenerateDialog(false)}
                        >
                            Cancel
                        </Button>
                        <Button variant="destructive" onClick={handleRegenerateKey}>
                            Regenerate
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}
