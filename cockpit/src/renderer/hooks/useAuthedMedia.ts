import { useEffect, useState } from 'react'
import { API_BASE, authHeader } from '../api/client'

/**
 * Resolve an auth-gated media URL into a browser-usable blob object URL.
 *
 * The chat media endpoints (`/api/umh/chat/media/{id}`, `/chat/attachment`) sit
 * behind the parent router's Clerk bearer dependency — HEADER-only auth, no
 * cookie/query fallback. A plain `<img src>` / `<video src>` / `<a href>` cannot
 * attach that bearer, so the browser's element GET 401s and the media never
 * renders. This hook fetches the URL WITH the Clerk bearer (authHeader, same as
 * the upload path), turns the response into an object URL, and revokes it on
 * unmount / url change so blobs don't leak.
 *
 * Returns { url, loading, error }:
 *  - url: the object URL to feed <img>/<video>/<a> (empty string until resolved).
 *  - loading: true while fetching.
 *  - error: a short reason string when the fetch/auth failed (else null).
 *
 * `rawUrl` may be an absolute URL, a `/api/umh/...` path, or already a blob:/data:
 * URL (returned as-is — no fetch needed, e.g. a client-side previewUrl).
 */
export function useAuthedMedia(rawUrl: string | undefined | null): {
  url: string
  loading: boolean
  error: string | null
} {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!rawUrl) {
      setUrl('')
      setError(null)
      setLoading(false)
      return
    }

    // Already directly usable — a client-side blob/data URL needs no auth fetch.
    if (rawUrl.startsWith('blob:') || rawUrl.startsWith('data:')) {
      setUrl(rawUrl)
      setError(null)
      setLoading(false)
      return
    }

    let objectUrl = ''
    let cancelled = false
    setLoading(true)
    setError(null)

    // Normalize a server path ("/api/umh/chat/media/x" or "/chat/media/x") to an
    // absolute URL rooted at the API origin. API_BASE ends with "/api/umh".
    const apiOrigin = API_BASE.replace(/\/api\/umh$/, '')
    const target = rawUrl.startsWith('http')
      ? rawUrl
      : rawUrl.startsWith('/api/umh')
        ? `${apiOrigin}${rawUrl}`
        : rawUrl.startsWith('/')
          ? `${API_BASE}${rawUrl}`
          : `${API_BASE}/${rawUrl}`

    ;(async () => {
      try {
        const res = await fetch(target, { headers: await authHeader() })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const blob = await res.blob()
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
        setLoading(false)
      } catch (e) {
        if (cancelled) return
        setError(e instanceof Error ? e.message : 'load failed')
        setLoading(false)
      }
    })()

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [rawUrl])

  return { url, loading, error }
}
