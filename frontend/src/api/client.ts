/**
 * API client for UMH Operator Workstation backend.
 */

const API_BASE = import.meta.env.VITE_API_URL as string || '';
const API_KEY = import.meta.env.VITE_API_KEY as string || 'dev-key-change-me';

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json() as Promise<T>;
}
