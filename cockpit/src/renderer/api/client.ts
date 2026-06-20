const API_BASE = import.meta.env.VITE_API_URL as string || '/api/umh'

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
  return ''
}

export function getWsToken(): string {
  return ''
}

export async function getClerkToken(): Promise<string | null> {
  if (!_getToken) return null
  return _getToken()
}

const _inflight = new Map<string, Promise<unknown>>()

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const method = (options?.method ?? 'GET').toUpperCase()
  if (method === 'GET') {
    const existing = _inflight.get(path) as Promise<T> | undefined
    if (existing) return existing
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  }

  if (_getToken) {
    const token = await _getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const promise = fetch(`${API_BASE}${path}`, { ...options, headers }).then(res => {
    if (!res.ok) throw new ApiError(res.status, `API ${res.status}: ${res.statusText}`)
    return res.json() as Promise<T>
  })

  if (method === 'GET') {
    _inflight.set(path, promise)
    promise.finally(() => _inflight.delete(path))
  }

  return promise
}
