"use client"

import * as React from "react"
import { ChevronsUpDown, Check, Plus, Building2 } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
    CommandSeparator,
} from "@/components/ui/command"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import { useTenant } from "@/context/tenant-context"
import { useRouter } from "next/navigation"

export function TenantSwitcher({ className }: { className?: string }) {
    const [open, setOpen] = React.useState(false)
    const { tenants, currentTenant, setCurrentTenant } = useTenant()
    const router = useRouter()

    const activeTenant = currentTenant || tenants[0]

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={open}
                    aria-label="Select a tenant"
                    className={cn("w-full justify-between", className)}
                >
                    <div className="flex items-center truncate">
                        <Building2 className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                        <span className="truncate">{activeTenant?.name || "Select Tenant"}</span>
                    </div>
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[200px] p-0">
                <Command>
                    <CommandList>
                        <CommandInput placeholder="Search tenant..." />
                        <CommandEmpty>No tenant found.</CommandEmpty>
                        <CommandGroup heading="Tenants">
                            {tenants.map((tenant) => (
                                <CommandItem
                                    key={tenant.id}
                                    onSelect={() => {
                                        setCurrentTenant(tenant)
                                        setOpen(false)
                                    }}
                                    className="text-sm"
                                >
                                    <Building2 className="mr-2 h-4 w-4 opacity-50" />
                                    {tenant.name}
                                    <Check
                                        className={cn(
                                            "ml-auto h-4 w-4",
                                            activeTenant?.id === tenant.id
                                                ? "opacity-100"
                                                : "opacity-0"
                                        )}
                                    />
                                </CommandItem>
                            ))}
                        </CommandGroup>
                    </CommandList>
                    <CommandSeparator />
                    <CommandList>
                        <CommandGroup>
                            <CommandItem
                                onSelect={() => {
                                    setOpen(false)
                                    router.push("/dashboard/tenants/create")
                                }}
                            >
                                <Plus className="mr-2 h-5 w-5" />
                                Create Workspace
                            </CommandItem>
                        </CommandGroup>
                    </CommandList>
                </Command>
            </PopoverContent>
        </Popover>
    )
}
