/**
 * /api/code routes
 *
 * Operations:
 *   POST /read    { path }            → { content }
 *   POST /write   { path, content }   → { ok: true }
 *   POST /execute { command }         → { output, exitCode }
 *   POST /list    { path }            → { entries: FileEntry[] }
 *
 * Security:
 *   - All paths are resolved relative to APP_ROOT (default /app)
 *   - Path traversal outside APP_ROOT is blocked
 *   - Execute: intentionally supports shell commands for operator terminal
 *     Auth-gated so only authenticated operators can use it
 *
 * Auth:
 *   - Checks CLAUDE_CODE_OAUTH_TOKEN header if configured
 */

import { Hono } from 'hono'
import { readFile, writeFile, stat, readdir } from 'fs/promises'
import { execFile } from 'child_process'
import { resolve, relative, join } from 'path'

const APP_ROOT = process.env.APP_ROOT ?? '/app'
const AUTH_TOKEN = process.env.CLAUDE_CODE_OAUTH_TOKEN ?? ''
const EXEC_TIMEOUT = Number(process.env.EXEC_TIMEOUT_MS ?? 30000)

export const codeRouter = new Hono()

// Auth middleware — if token is configured, require it
codeRouter.use('*', async (c, next) => {
  if (AUTH_TOKEN) {
    const header = c.req.header('x-auth-token') || ''
    if (header !== AUTH_TOKEN) {
      return c.json({ error: 'unauthorized' }, 401)
    }
  }
  await next()
})

/** Resolve and validate a path is within APP_ROOT */
function safePath(inputPath: string): string | null {
  const resolved = resolve(APP_ROOT, inputPath)
  const rel = relative(APP_ROOT, resolved)
  if (rel.startsWith('..') || resolve(APP_ROOT, rel) !== resolved) {
    return null
  }
  return resolved
}

// ── READ ─────────────────────────────────────────────────────────────────────

codeRouter.post('/read', async (c) => {
  const body = await c.req.json<{ path: string }>()
  if (!body.path) return c.json({ error: 'path required' }, 400)

  const resolved = safePath(body.path)
  if (!resolved) return c.json({ error: 'path traversal blocked' }, 403)

  try {
    const content = await readFile(resolved, 'utf-8')
    return c.json({ content })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    if (msg.includes('ENOENT')) return c.json({ error: 'file not found' }, 404)
    return c.json({ error: msg }, 500)
  }
})

// ── WRITE ────────────────────────────────────────────────────────────────────

codeRouter.post('/write', async (c) => {
  const body = await c.req.json<{ path: string; content: string }>()
  if (!body.path) return c.json({ error: 'path required' }, 400)
  if (body.content === undefined) return c.json({ error: 'content required' }, 400)

  const resolved = safePath(body.path)
  if (!resolved) return c.json({ error: 'path traversal blocked' }, 403)

  try {
    await writeFile(resolved, body.content, 'utf-8')
    return c.json({ ok: true })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    return c.json({ error: msg }, 500)
  }
})

// ── EXECUTE ──────────────────────────────────────────────────────────────────
// Uses execFile with bash -c to execute operator commands.
// Auth-gated: only authenticated operators can use this endpoint.

codeRouter.post('/execute', async (c) => {
  const body = await c.req.json<{ command: string }>()
  if (!body.command) return c.json({ error: 'command required' }, 400)

  return new Promise<Response>((resolvePromise) => {
    execFile(
      '/bin/bash',
      ['-c', body.command],
      { cwd: APP_ROOT, timeout: EXEC_TIMEOUT, maxBuffer: 1024 * 1024 },
      (err, stdout, stderr) => {
        const output = stdout + (stderr ? `\n${stderr}` : '')
        const exitCode = err ? (err as NodeJS.ErrnoException & { code?: number }).code ?? 1 : 0
        resolvePromise(c.json({ output: output.trimEnd(), exitCode: typeof exitCode === 'number' ? exitCode : 1 }))
      }
    )
  })
})

// ── LIST ─────────────────────────────────────────────────────────────────────

codeRouter.post('/list', async (c) => {
  const body = await c.req.json<{ path: string }>()
  if (!body.path) return c.json({ error: 'path required' }, 400)

  const resolved = safePath(body.path)
  if (!resolved) return c.json({ error: 'path traversal blocked' }, 403)

  try {
    const items = await readdir(resolved, { withFileTypes: true })
    const entries = items
      .filter((item) => !item.name.startsWith('.')) // hide dotfiles by default
      .map((item) => ({
        name: item.name,
        path: join(body.path, item.name),
        type: item.isDirectory() ? 'directory' : 'file',
      }))
    return c.json({ entries })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    if (msg.includes('ENOENT')) return c.json({ error: 'directory not found' }, 404)
    return c.json({ error: msg }, 500)
  }
})
