export const API_BASE = import.meta.env.VITE_API_URL as string || '/api/umh'

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
  if (_getToken) {
    try {
      const t = await _getToken()
      if (t) return t
    } catch { /* fall through */ }
  }
  if (window.Clerk?.session) {
    try { return await window.Clerk.session.getToken() } catch { /* fall through */ }
  }
  return null
}

async function freshToken(): Promise<string | null> {
  if (window.Clerk?.session) {
    try {
      const t = await window.Clerk.session.getToken({ skipCache: true })
      if (t) return t
    } catch { /* fall through */ }
  }
  if (_getToken) {
    try { return await _getToken() } catch { /* fall through */ }
  }
  return null
}

const _inflight = new Map<string, Promise<unknown>>()

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const method = (options?.method ?? 'GET').toUpperCase()
  if (method === 'GET') {
    const existing = _inflight.get(path) as Promise<T> | undefined
    if (existing) return existing
  }

  const doFetch = async (attempt: number): Promise<T> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options?.headers as Record<string, string>),
    }

    const token = attempt > 0 ? await freshToken() : await getClerkToken()
    if (!token && attempt < 3) {
      await new Promise(r => setTimeout(r, 500 * (attempt + 1)))
      return doFetch(attempt + 1)
    }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const controller = new AbortController()
    const isConverse = path.includes('/converse')
    const isApproveOrDispatch = path.includes('/approve') || path.includes('/dispatch')
    const timeoutMs = isConverse ? 120_000 : isApproveOrDispatch ? 120_000 : 60_000
    const timeoutId = setTimeout(() => controller.abort(`${method} ${path} timed out after ${timeoutMs / 1000}s`), timeoutMs)
    let res: Response
    try {
      res = await fetch(`${API_BASE}${path}`, { ...options, headers, signal: controller.signal })
    } catch (err) {
      clearTimeout(timeoutId)
      const isAbort = err instanceof DOMException && err.name === 'AbortError'
      if (method === 'GET' && attempt < 3 && !isAbort) {
        await new Promise(r => setTimeout(r, 2000 * (attempt + 1)))
        return doFetch(attempt + 1)
      }
      if (isAbort) {
        const reason = controller.signal.reason || `${method} ${path} aborted`
        throw new ApiError(0, reason)
      }
      throw err
    }
    clearTimeout(timeoutId)
    if (res.status === 401 && attempt < 3) {
      await new Promise(r => setTimeout(r, 1000))
      return doFetch(attempt + 1)
    }
    if (method === 'GET' && (res.status === 502 || res.status === 504) && attempt < 3) {
      await new Promise(r => setTimeout(r, 2000 * (attempt + 1)))
      return doFetch(attempt + 1)
    }
    if (!res.ok) {
      let detail = res.statusText
      try {
        const body = await res.json()
        if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
        else if (body?.error) detail = typeof body.error === 'string' ? body.error : JSON.stringify(body.error)
        else if (body?.message) detail = body.message
      } catch { /* response wasn't JSON — use statusText */ }
      throw new ApiError(res.status, detail)
    }
    return res.json() as Promise<T>
  }

  const promise = doFetch(0)

  if (method === 'GET') {
    _inflight.set(path, promise)
    promise.finally(() => _inflight.delete(path))
  }

  return promise
}
