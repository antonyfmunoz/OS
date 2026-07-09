import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchApi, ApiError, setTokenGetter } from '../api/client'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
  vi.stubGlobal('Clerk', undefined)
  setTokenGetter(async () => 'hdr.pay.sig')
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('fetchApi — auth headers', () => {
  it('attaches Bearer token from getter', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ok' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await fetchApi('/organism/status')

    const [, opts] = mockFetch.mock.calls[0]
    expect(opts.headers.Authorization).toBe('Bearer hdr.pay.sig')
  })
})

describe('fetchApi — error handling', () => {
  it('throws ApiError on non-ok response (non-retryable status)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      json: async () => ({ detail: 'Access denied' }),
    }))

    await expect(fetchApi('/mutations/submit', { method: 'POST' }))
      .rejects.toThrow(ApiError)
  })

  it('parses detail from JSON error body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: async () => ({ detail: 'Invalid mutation_name' }),
    }))

    try {
      await fetchApi('/mutations/submit', { method: 'POST' })
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).message).toBe('Invalid mutation_name')
      expect((err as ApiError).status).toBe(422)
    }
  })
})

describe('fetchApi — GET deduplication', () => {
  it('deduplicates concurrent GET requests to the same path', async () => {
    let resolveFirst: (v: unknown) => void
    const mockFetch = vi.fn().mockImplementation(
      () => new Promise(resolve => { resolveFirst = resolve })
    )
    vi.stubGlobal('fetch', mockFetch)

    const p1 = fetchApi('/organism/status')
    const p2 = fetchApi('/organism/status')

    // fetchApi awaits the token getter before calling fetch — wait for the
    // mock to actually be invoked before resolving it.
    await vi.waitFor(() => expect(mockFetch).toHaveBeenCalled())
    resolveFirst!({ ok: true, json: async () => ({ data: 1 }) })

    const [r1, r2] = await Promise.all([p1, p2])
    expect(r1).toEqual(r2)
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })
})
