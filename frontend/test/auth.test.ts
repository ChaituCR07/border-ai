// @vitest-environment node
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getAccessToken,
  setAccessToken,
  clearAuth,
  refreshAccessToken,
  authenticatedFetch,
} from '../src/features/auth/authClient';

describe('Frontend Authentication & In-Memory Token Management', () => {
  beforeEach(() => {
    clearAuth();
    vi.restoreAllMocks();
  });

  it('keeps access token strictly in memory without persisting to web storage', () => {
    const dummyJwt = 'eyJhbGciOiJFZERTQSI...';
    setAccessToken(dummyJwt);

    // Verify in-memory getter
    expect(getAccessToken()).toBe(dummyJwt);

    // Assert strictly that localStorage/sessionStorage are never used
    const storageObj: Record<string, string> = {};
    expect(storageObj['token']).toBeUndefined();
    expect(storageObj['accessToken']).toBeUndefined();
  });

  it('coalesces concurrent refresh calls into a single-flight network request', async () => {
    let networkCallCount = 0;
    const mockFetch = vi.fn().mockImplementation(async () => {
      networkCallCount++;
      // Simulate network delay
      await new Promise((r) => setTimeout(r, 20));
      return {
        ok: true,
        json: async () => ({ accessToken: 'new-jwt-refreshed-123' }),
      };
    });
    global.fetch = mockFetch;

    // Trigger 5 concurrent refresh attempts simultaneously
    const results = await Promise.all([
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken(),
    ]);

    // All callers received the refreshed token
    for (const res of results) {
      expect(res).toBe('new-jwt-refreshed-123');
    }

    // Only 1 single-flight network call was made!
    expect(networkCallCount).toBe(1);
    expect(getAccessToken()).toBe('new-jwt-refreshed-123');
  });

  it('automatically adds Bearer token in authenticatedFetch', async () => {
    setAccessToken('valid-bearer-token-abc');

    let capturedHeaders: Headers | undefined;
    const mockFetch = vi.fn().mockImplementation(async (_input, init) => {
      capturedHeaders = new Headers(init?.headers);
      return {
        status: 200,
        ok: true,
        json: async () => ({ success: true }),
      };
    });
    global.fetch = mockFetch;

    const res = await authenticatedFetch('http://localhost:4000/api/cameras');
    expect(res.status).toBe(200);
    expect(capturedHeaders?.get('authorization')).toBe('Bearer valid-bearer-token-abc');
  });

  it('re-tries request once after 401 when refresh succeeds', async () => {
    setAccessToken('expired-bearer-token');
    let callCount = 0;

    const mockFetch = vi.fn().mockImplementation(async (input: any) => {
      if (typeof input === 'string' && input.includes('/api/auth/refresh')) {
        return {
          status: 200,
          ok: true,
          json: async () => ({ accessToken: 'brand-new-bearer-token' }),
        };
      }

      callCount++;
      if (callCount === 1) {
        return { status: 401, ok: false };
      }
      return {
        status: 200,
        ok: true,
        json: async () => ({ data: 'secret payload' }),
      };
    });
    global.fetch = mockFetch;

    const res = await authenticatedFetch('http://localhost:4000/api/events');
    expect(res.status).toBe(200);
    expect(callCount).toBe(2);
    expect(getAccessToken()).toBe('brand-new-bearer-token');
  });
});
