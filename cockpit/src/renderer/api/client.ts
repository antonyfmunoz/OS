const API_BASE = import.meta.env.VITE_API_URL as string || '/api/umh'
const API_KEY = import.meta.env.VITE_UMH_API_KEY as string || ''

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

let _getToken: (() => Promise<string | null>) | null = null

export function setTokenGetter(fn: () => Promise<string | null>) {
  _getToken = fn
}

export function getApiKey(): string {
  return API_KEY
}

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  }

  if (API_KEY) {
    headers['X-API-Key'] = API_KEY
  }

  if (_getToken) {
    const token = await _getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    throw new ApiError(res.status, `API ${res.status}: ${res.statusText}`)
  }
  return res.json() as Promise<T>
}
