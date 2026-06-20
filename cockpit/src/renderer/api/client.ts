const API_BASE = import.meta.env.VITE_API_URL as string || '/api/umh'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

let _getToken: (() => Promise<string | null>) | null = null
let _tokenReady: Promise<void> | null = null
let _resolveTokenReady: (() => void) | null = null

export function setTokenGetter(fn: () => Promise<string | null>) {
  _getToken = fn
  const tryResolve = () => {
    fn().then((t) => {
      if (t && _resolveTokenReady) { _resolveTokenReady(); _resolveTokenReady = null }
      else if (!t && _resolveTokenReady) setTimeout(tryResolve, 200)
    })
  }
  tryResolve()
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

export function waitForToken(timeoutMs = 5000): Promise<void> {
  if (!_tokenReady) {
    _tokenReady = new Promise((resolve) => {
      _resolveTokenReady = resolve
      setTimeout(() => { resolve(); _resolveTokenReady = null }, timeoutMs)
      if (_getToken) {
        _getToken().then((t) => {
          if (t) { resolve(); _resolveTokenReady = null }
        })
      }
    })
  }
  return _tokenReady
}

const _inflight = new Map<string, Promise<unknown>>()

async function _doFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  }

  if (_getToken) {
    const token = await _getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) throw new ApiError(res.status, `API ${res.status}: ${res.statusText}`)
  return res.json() as Promise<T>
}

const _wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const method = (options?.method ?? 'GET').toUpperCase()
  if (method === 'GET') {
    const existing = _inflight.get(path) as Promise<T> | undefined
    if (existing) return existing
  }

  const promise = _doFetch<T>(path, options).catch(async (err) => {
    if (!(err instanceof ApiError && err.status === 401 && _getToken)) throw err
    for (const delay of [500, 1500, 3000]) {
      await _wait(delay)
      try { return await _doFetch<T>(path, options) } catch (e) {
        if (!(e instanceof ApiError && e.status === 401)) throw e
      }
    }
    throw err
  })

  if (method === 'GET') {
    _inflight.set(path, promise)
    promise.finally(() => _inflight.delete(path))
  }

  return promise
}
