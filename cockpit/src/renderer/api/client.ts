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

/** A signed Clerk session token is a JWT: three non-empty base64url segments joined
 *  by dots (header.payload.signature). Clerk's getToken() can transiently return a
 *  NON-JWT truthy string on mobile Safari (a handshake/dev-browser/opaque value); if
 *  that reaches a `bearer.<X>` WS subprotocol the server's JWT parse fails with
 *  "Not enough segments" → 403 (P4S-VOICE-WS-FRAMELESS-SOCKET-002). Shape-guard here
 *  so a non-JWT is treated as "no token" by EVERY caller (event/broadcast/voice WS),
 *  never sent as a bogus credential. */
function _isJwtShaped(t: string): boolean {
  const parts = t.split('.')
  return parts.length === 3 && parts.every((p) => p.length > 0)
}

export async function getClerkToken(): Promise<string | null> {
  if (_getToken) {
    try {
      const t = await _getToken()
      if (t && _isJwtShaped(t)) return t
    } catch { /* fall through */ }
  }
  if (window.Clerk?.session) {
    try {
      const t = await window.Clerk.session.getToken()
      if (t && _isJwtShaped(t)) return t
    } catch { /* fall through */ }
  }
  return null
}

async function freshToken(): Promise<string | null> {
  if (window.Clerk?.session) {
    try {
      const t = await window.Clerk.session.getToken({ skipCache: true })
      if (t && _isJwtShaped(t)) return t
    } catch { /* fall through */ }
  }
  if (_getToken) {
    try {
      const t = await _getToken()
      if (t && _isJwtShaped(t)) return t
    } catch { /* fall through */ }
  }
  return null
}

/** Distinct outcomes of a bounded token acquisition, so callers can emit a PRECISE
 *  typed failure instead of a generic one. `token` is set only on 'ok'. */
export type TokenAcquireResult =
  | { status: 'ok'; token: string }
  | { status: 'missing' }   // Clerk answered, but there is no token (not signed in)
  | { status: 'timeout' }   // Clerk's getToken() stalled past the budget (mobile Safari)

/**
 * Acquire a Clerk token under a HARD time budget, with one skipCache retry.
 *
 * WHY: on mobile Safari `window.Clerk.session.getToken()` can stall indefinitely
 * (session rehydration / network). The voice-WS connect path used to `await
 * getClerkToken()` with no bound, so a stalled getter consumed the entire
 * voice-start budget and the outer 8s watchdog fired with a FALSE "server
 * unreachable" (P4S-VOICE-WS-AUTH-PREFLIGHT-001). This bounds it: a stall becomes a
 * fast, typed 'timeout' — never an unbounded hang, never a mislabeled failure.
 *
 * Budget split: race the (possibly cached) fetch for the first ~60% of `budgetMs`;
 * if that stalls, race a skipCache `freshToken()` for the remainder. If BOTH stall,
 * return 'timeout'. If either resolves to null, return 'missing'.
 */
export async function acquireClerkToken(budgetMs = 3000): Promise<TokenAcquireResult> {
  const firstBudget = Math.max(500, Math.floor(budgetMs * 0.6))
  const timedOut = Symbol('token_timeout')

  const race = (p: Promise<string | null>, ms: number) =>
    new Promise<string | null | typeof timedOut>((resolve) => {
      const t = setTimeout(() => resolve(timedOut), ms)
      p.then(
        (v) => { clearTimeout(t); resolve(v) },
        () => { clearTimeout(t); resolve(null) },
      )
    })

  const first = await race(getClerkToken(), firstBudget)
  if (typeof first === 'string' && first) return { status: 'ok', token: first }
  if (first === null) return { status: 'missing' }

  // first stalled — one bounded skipCache retry with the remaining budget.
  const second = await race(freshToken(), Math.max(500, budgetMs - firstBudget))
  if (typeof second === 'string' && second) return { status: 'ok', token: second }
  if (second === null) return { status: 'missing' }
  return { status: 'timeout' }
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
