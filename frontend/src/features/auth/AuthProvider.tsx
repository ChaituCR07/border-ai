import React, { createContext, useContext, useEffect, useState, useMemo } from 'react';
import type { AuthUser, UserRole } from './types';
import {
  getAccessToken,
  setAccessToken,
  clearAuth,
  refreshAccessToken,
  authenticatedFetch,
} from './authClient';

const ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  ADMIN: ['*'],
  INVESTIGATOR: [
    'events:view', 'events:export',
    'alerts:view', 'alerts:ack', 'alerts:note', 'alerts:escalate',
    'cameras:view', 'cameras:ptz',
    'stream:live', 'evidence:view', 'evidence:export',
    'investigation:search', 'investigation:report',
    'watchlist:view', 'watchlist:manage',
    'correlation:view', 'correlation:query',
    'analytics:view', 'analytics:export',
    'config:view',
    'notifications:view', 'notifications:test',
    'system:status', 'system:metrics',
  ],
  OPERATOR: [
    'events:view',
    'alerts:view', 'alerts:ack', 'alerts:note',
    'cameras:view', 'cameras:ptz',
    'stream:live', 'evidence:view',
    'watchlist:view',
    'correlation:view',
    'analytics:view',
    'system:status',
  ],
  VIEWER: [
    'events:view',
    'alerts:view',
    'cameras:view',
    'stream:live',
    'analytics:view',
    'system:status',
  ],
};

export interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (u: string, p: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initial silent refresh attempt on application mount
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const token = await refreshAccessToken();
        if (token && mounted) {
          const res = await authenticatedFetch('/api/auth/me');
          if (res.ok) {
            const data = await res.json();
            setUser(data.user);
          }
        }
      } catch {
        // Not authenticated
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const login = async (username: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();
      if (!res.ok) {
        return { success: false, error: data?.error?.message || data?.message || 'Login failed' };
      }

      setAccessToken(data.accessToken);
      setUser(data.user);
      return { success: true };
    } catch (err: any) {
      return { success: false, error: err?.message || 'Network error during login' };
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await authenticatedFetch('/api/auth/logout', { method: 'POST' });
    } catch {
      // Ignore network errors on logout
    } finally {
      clearAuth();
      setUser(null);
    }
  };

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    if (user.role === 'ADMIN') return true;
    const perms = ROLE_PERMISSIONS[user.role] || [];
    return perms.includes('*') || perms.includes(permission);
  };

  const contextValue = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      logout,
      hasPermission,
    }),
    [user, isLoading]
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
