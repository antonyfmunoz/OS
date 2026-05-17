/**
 * Code Engine API client
 * Wraps calls to the operator backend which delegates to saas-dev-skill.
 *
 * Contract:
 *   read(path)           → { content: string }
 *   write(path, content) → { ok: true }
 *   execute(command)     → { output: string, exitCode: number }
 *   listDir(path)        → { entries: FileEntry[] }
 */

export interface FileEntry {
  name: string
  path: string
  type: 'file' | 'directory'
}

export interface ReadResult {
  content: string
}

export interface WriteResult {
  ok: boolean
}

export interface ExecResult {
  output: string
  exitCode: number
}

export interface ListResult {
  entries: FileEntry[]
}

const BASE = '/api/code'

async function request<T>(endpoint: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || `API error ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function readFile(path: string): Promise<ReadResult> {
  return request<ReadResult>('/read', { path })
}

export async function writeFile(path: string, content: string): Promise<WriteResult> {
  return request<WriteResult>('/write', { path, content })
}

export async function execute(command: string): Promise<ExecResult> {
  return request<ExecResult>('/execute', { command })
}

export async function listDir(path: string): Promise<ListResult> {
  return request<ListResult>('/list', { path })
}
