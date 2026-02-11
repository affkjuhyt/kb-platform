"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
    LayoutDashboard,
    Files,
    Settings,
    Database,
    Search,
    Users,
    LogOut
} from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { TenantSwitcher } from "@/components/tenant-switcher"
import { useAuth } from "@/context/auth-context"

export function Sidebar() {
    const pathname = usePathname()
    const { logout } = useAuth()

    const routes = [
        {
            label: "Dashboard",
            icon: LayoutDashboard,
            href: "/dashboard",
            active: pathname === "/dashboard",
        },
        {
            label: "Knowledge Bases",
            icon: Database,
            href: "/dashboard/kb",
            active: pathname.startsWith("/dashboard/kb"),
        },
        {
            label: "Documents",
            icon: Files,
            href: "/dashboard/documents",
            active: pathname.startsWith("/dashboard/documents"),
        },
        {
            label: "Playground",
            icon: Search,
            href: "/dashboard/playground",
            active: pathname.startsWith("/dashboard/playground"),
        },
        {
            label: "Tenants",
            icon: Users,
            href: "/dashboard/tenants",
            active: pathname.startsWith("/dashboard/tenants"),
        },
        {
            label: "Settings",
            icon: Settings,
            href: "/dashboard/settings",
            active: pathname.startsWith("/dashboard/settings"),
        },
    ]

    return (
        <div className="space-y-4 py-4 flex flex-col h-full bg-secondary/10 border-r">
            <div className="px-3 py-2">
                <Link href="/dashboard" className="flex items-center pl-3 mb-14">
                    <div className="relative w-8 h-8 mr-4">
                        {/* Logo placeholder */}
                        <div className="bg-primary rounded-lg w-full h-full flex items-center justify-center text-primary-foreground font-bold">
                            KB
                        </div>
                    </div>
                    <h1 className="text-xl font-bold">
                        Nexus Platform
                    </h1>
                </Link>
                <div className="mb-4 px-3">
                    <TenantSwitcher />
                </div>
                <div className="space-y-1">
                    {routes.map((route) => (
                        <Button
                            key={route.href}
                            variant={route.active ? "secondary" : "ghost"}
                            className={cn(
                                "w-full justify-start",
                                route.active ? "bg-secondary" : "transparent"
                            )}
                            asChild
                        >
                            <Link href={route.href}>
                                <route.icon className="h-5 w-5 mr-3" />
                                {route.label}
                            </Link>
                        </Button>
                    ))}
                </div>
            </div>

            <div className="mt-auto px-4 py-4 border-t border-secondary-foreground/10">
                <Button
                    variant="ghost"
                    className="w-full justify-start text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    onClick={() => logout()}
                >
                    <LogOut className="h-5 w-5 mr-3" />
                    Log Out
                </Button>
            </div>
        </div>
    )
}
