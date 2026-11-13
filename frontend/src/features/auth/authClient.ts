import type { AuthUser } from './types';

let inMemoryAccessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || '';

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

export function clearAuth(): void {
  inMemoryAccessToken = null;
  refreshPromise = null;
}

/**
 * Single-flight silent refresh mutex.
 * Multiple concurrent callers will await the exact same in-flight refresh request.
 */
export async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRF-Token': 'csrf-client-header',
        },
      });

      if (!res.ok) {
        clearAuth();
        return null;
      }

      const data = await res.json();
      if (data?.accessToken) {
        setAccessToken(data.accessToken);
        return data.accessToken;
      }
      clearAuth();
      return null;
    } catch {
      clearAuth();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Fetch wrapper that attaches in-memory access token, catches 401s,
 * performs single-flight silent refresh, and retries the request once.
 */
export async function authenticatedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(init.headers || {});

  const token = getAccessToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const res = await fetch(input, {
    ...init,
    headers,
    credentials: 'include',
  });

  // If 401 Unauthorized, attempt silent token refresh and replay once
  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const retryHeaders = new Headers(init.headers || {});
      retryHeaders.set('Authorization', `Bearer ${newToken}`);
      return fetch(input, {
        ...init,
        headers: retryHeaders,
        credentials: 'include',
      });
    }
  }

  return res;
}
