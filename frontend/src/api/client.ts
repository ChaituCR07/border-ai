import createClient from 'openapi-fetch';
import type { paths } from './schema';
import { ApiError } from './errors';

const defaultBase =
  typeof window !== 'undefined' && window.location?.origin && window.location.origin !== 'null'
    ? window.location.origin
    : 'http://localhost:3000';

const baseUrl = import.meta.env.VITE_API_BASE_URL || defaultBase;

export const api = createClient<paths>({
  baseUrl,
  fetch: (...args) => fetch(...args),
});

export async function unwrap<T>(
  promise: Promise<{ data?: T; error?: unknown; response: Response }>
): Promise<T> {
  const { data, error, response } = await promise;
  if (error || data === undefined) {
    const errPayload = error as
      | { error?: { code?: string; message?: string; request_id?: string; details?: unknown } }
      | undefined;
    const code = errPayload?.error?.code ?? `HTTP_${response.status}`;
    const message = errPayload?.error?.message ?? response.statusText ?? 'Unknown API Error';
    const requestId = errPayload?.error?.request_id ?? response.headers.get('x-request-id') ?? undefined;
    throw new ApiError(response.status, code, message, requestId, errPayload?.error?.details);
  }
  return data;
}
