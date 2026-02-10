"use client"

import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { Tenant } from '@/types/tenant';
import { tenantApi } from '@/lib/api/tenants';
import { useAuth } from '@/context/auth-context';
import { toast } from 'sonner';

interface TenantContextType {
    tenants: Tenant[];
    currentTenant: Tenant | null;
    isLoading: boolean;
    setCurrentTenant: (tenant: Tenant) => void;
    refreshTenants: () => Promise<void>;
}

const TenantContext = createContext<TenantContextType | undefined>(undefined);

export function TenantProvider({ children }: { children: React.ReactNode }) {
    const { user, token } = useAuth();
    const [tenants, setTenants] = useState<Tenant[]>([]);
    const [currentTenant, setCurrentTenantState] = useState<Tenant | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const refreshTenants = useCallback(async () => {
        if (!token) return;

        try {
            setIsLoading(true);
            const data = await tenantApi.list();
            setTenants(data);

            // Handle current tenant persistence
            const savedTenantId = localStorage.getItem('currentTenantId');

            if (savedTenantId) {
                const found = data.find(t => t.id === savedTenantId);
                if (found) {
                    setCurrentTenantState(found);
                } else if (data.length > 0) {
                    // Fallback to first available if saved one not found
                    setCurrentTenant(data[0]);
                }
            } else if (data.length > 0) {
                // Default to first available
                setCurrentTenant(data[0]);
            }
        } catch (error) {
            console.error('Failed to fetch tenants:', error);
            toast.error('Failed to load tenants');
        } finally {
            setIsLoading(false);
        }
    }, [token]);

    const setCurrentTenant = (tenant: Tenant) => {
        setCurrentTenantState(tenant);
        localStorage.setItem('currentTenantId', tenant.id);
        // We might want to trigger other updates here or update cookies if backend needs it
    };

    useEffect(() => {
        if (user && token) {
            refreshTenants();
        } else {
            setTenants([]);
            setCurrentTenantState(null);
            setIsLoading(false);
        }
    }, [user, token, refreshTenants]);

    return (
        <TenantContext.Provider value={{
            tenants,
            currentTenant,
            isLoading,
            setCurrentTenant,
            refreshTenants
        }}>
            {children}
        </TenantContext.Provider>
    );
}

export function useTenant() {
    const context = useContext(TenantContext);
    if (context === undefined) {
        throw new Error('useTenant must be used within a TenantProvider');
    }
    return context;
}
