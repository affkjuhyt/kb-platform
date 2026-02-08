"use client"

import { createContext, useContext, useEffect, useState } from 'react';
import Cookies from 'js-cookie';
import { jwtDecode } from 'jwt-decode';
import { useRouter, usePathname } from 'next/navigation';
import axios from 'axios';
import { User } from '@/types/auth';

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string) => void;
    logout: () => void;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    const login = (newToken: string) => {
        Cookies.set('token', newToken, { expires: 1 }); // 1 day
        setToken(newToken);
        const decoded = jwtDecode<{ sub: string; email: string; role: string; tenant_id: string; exp: number }>(newToken);
        setUser({
            id: decoded.sub,
            email: decoded.email,
            role: decoded.role,
            tenant_id: decoded.tenant_id,
        });
        axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
        router.push('/dashboard');
    };

    const logout = () => {
        Cookies.remove('token');
        setToken(null);
        setUser(null);
        delete axios.defaults.headers.common['Authorization'];
        router.push('/login');
    };

    useEffect(() => {
        const initAuth = () => {
            const storedToken = Cookies.get('token');
            if (storedToken) {
                try {
                    const decoded = jwtDecode<{ sub: string; email: string; role: string; tenant_id: string; exp: number }>(storedToken);
                    // Check if token is expired
                    if (decoded.exp * 1000 < Date.now()) {
                        logout();
                    } else {
                        setToken(storedToken);
                        setUser({
                            id: decoded.sub,
                            email: decoded.email,
                            role: decoded.role,
                            tenant_id: decoded.tenant_id,
                        });
                        // Setup axios default header
                        axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
                    }
                } catch (error) {
                    console.error('Invalid token:', error);
                    logout();
                }
            }
            setIsLoading(false);
        };

        initAuth();
    }, []);

    // Protect routes
    useEffect(() => {
        if (!isLoading && !user && !pathname.startsWith('/login') && !pathname.startsWith('/register')) {
            router.push('/login');
        }
    }, [user, isLoading, pathname, router]);

    return (
        <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
