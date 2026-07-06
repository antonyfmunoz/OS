// WP-P4-COCKPIT-BROWSER-VERIFY-001 — randomId must work in insecure contexts.
// crypto.randomUUID only exists in secure contexts; canvas windows could never
// spawn on plain-http origins because addWindow threw (found in live browser
// verification, not by unit tests — keep this regression pinned).
import { describe, it, expect, vi, afterEach } from 'vitest'
import { randomId } from '../utils/ids'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('randomId', () => {
  it('uses crypto.randomUUID when available', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'uuid-from-crypto' })
    expect(randomId()).toBe('uuid-from-crypto')
  })

  it('falls back when crypto.randomUUID is missing (insecure context)', () => {
    vi.stubGlobal('crypto', {})
    const a = randomId()
    const b = randomId()
    expect(a).toMatch(/^id-/)
    expect(a).not.toBe(b)
  })

  it('canvasStore mints window ids through randomId, not crypto.randomUUID', async () => {
    const { readFileSync } = await import('node:fs')
    const { resolve, dirname } = await import('node:path')
    const { fileURLToPath } = await import('node:url')
    const dir = dirname(fileURLToPath(import.meta.url))
    const src = readFileSync(resolve(dir, '../stores/canvasStore.ts'), 'utf-8')
    expect(src).not.toContain('crypto.randomUUID()')
    expect(src).toContain("import { randomId } from '../utils/ids'")
  })
})
