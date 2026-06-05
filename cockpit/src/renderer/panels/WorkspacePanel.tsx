import { useState, useCallback, useEffect } from 'react'
import { clsx } from 'clsx'
import { usePolling } from '../hooks/usePolling'

type Tab = 'files' | 'diff' | 'tests' | 'logs' | 'proof' | 'health'

interface FileEntry {
  name: string
  path: string
  type: 'file' | 'directory'
  size: number
  source_env: string
}

interface GitChanged {
  status: string
  path: string
}

export function WorkspacePanel() {
  const [activeTab, setActiveTab] = useState<Tab>('files')

  const tabs: { id: Tab; label: string }[] = [
    { id: 'files', label: 'Files' },
    { id: 'diff', label: 'Diff' },
    { id: 'tests', label: 'Tests' },
    { id: 'logs', label: 'Logs' },
    { id: 'proof', label: 'Proof' },
    { id: 'health', label: 'Health' },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex items-center h-8 shrink-0 border-b border-border bg-canvas px-2 gap-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={clsx(
              'px-2.5 py-1 text-[11px] font-mono rounded transition-colors',
              activeTab === t.id
                ? 'text-cyan bg-cyan-glow'
                : 'text-text-tertiary hover:text-text-secondary',
            )}
          >
            {t.label}
          </button>
        ))}
        <div className="flex-1" />
        <span className="wv-label text-[10px]">Workspace</span>
      </div>

      {/* Tab content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === 'files' && <FileBrowserPane />}
        {activeTab === 'diff' && <DiffPane />}
        {activeTab === 'tests' && <TestResultsPane />}
        {activeTab === 'logs' && <LogsPane />}
        {activeTab === 'proof' && <ProofPane />}
        {activeTab === 'health' && <HealthPane />}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Files pane
// ---------------------------------------------------------------------------

function FileBrowserPane() {
  const [entries, setEntries] = useState<FileEntry[]>([])
  const [currentPath, setCurrentPath] = useState('/opt/OS')
  const [fileContent, setFileContent] = useState<string | null>(null)
  const [fileLang, setFileLang] = useState('plaintext')
  const [fileName, setFileName] = useState('')
  const [sourceEnv, setSourceEnv] = useState('')
  const [error, setError] = useState('')

  const browse = useCallback(async (path: string) => {
    try {
      const res = await fetch(`/api/umh/workspace/browse?path=${encodeURIComponent(path)}`)
      const data = await res.json()
      if (data.ok) {
        setEntries(data.entries)
        setCurrentPath(data.path)
        setSourceEnv(data.source_env)
        setError('')
      } else {
        setError(data.error || 'Browse failed')
      }
    } catch { setError('Network error') }
  }, [])

  useEffect(() => { browse(currentPath) }, [])

  const readFile = async (path: string, name: string) => {
    try {
      const res = await fetch(`/api/umh/workspace/read-file?path=${encodeURIComponent(path)}`)
      const data = await res.json()
      if (data.ok) {
        setFileContent(data.content)
        setFileLang(data.language)
        setFileName(name)
      }
    } catch { /* noop */ }
  }

  return (
    <div className="flex h-full">
      {/* Tree */}
      <div className="w-56 shrink-0 overflow-y-auto border-r border-border bg-canvas">
        <div className="px-3 py-2 border-b border-border flex items-center justify-between">
          <p className="wv-label">Explorer</p>
          {sourceEnv && <span className="text-[9px] font-mono text-text-tertiary">{sourceEnv}</span>}
        </div>
        {currentPath !== '/opt/OS' && (
          <button
            onClick={() => browse(currentPath.split('/').slice(0, -1).join('/') || '/opt/OS')}
            className="w-full text-left px-3 py-1 text-[11px] text-cyan hover:bg-surface-raised"
          >
            ← ..
          </button>
        )}
        {error && <p className="px-3 py-2 text-[11px] text-danger">{error}</p>}
        {entries.map((e) => (
          <button
            key={e.path}
            onClick={() => e.type === 'directory' ? browse(e.path) : readFile(e.path, e.name)}
            className={clsx(
              'w-full text-left flex items-center gap-1.5 px-3 py-0.5 text-[11px] hover:bg-surface-raised transition-colors',
              e.type === 'directory' ? 'text-text-primary' : 'text-text-secondary',
            )}
          >
            <span className="text-text-tertiary w-3 text-center">
              {e.type === 'directory' ? '▸' : '·'}
            </span>
            <span className="truncate">{e.name}</span>
            {e.type === 'file' && e.size > 0 && (
              <span className="ml-auto text-[9px] text-text-tertiary shrink-0">
                {e.size > 1024 ? `${(e.size / 1024).toFixed(0)}K` : `${e.size}B`}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* File viewer */}
      <div className="flex-1 flex flex-col min-w-0">
        {fileContent !== null ? (
          <>
            <div className="px-3 py-1.5 border-b border-border bg-canvas flex items-center gap-2">
              <span className="text-[11px] font-mono text-text-primary">{fileName}</span>
              <span className="text-[9px] font-mono text-text-tertiary">{fileLang}</span>
            </div>
            <pre className="flex-1 overflow-auto p-3 font-mono text-[11px] text-text-secondary bg-surface whitespace-pre-wrap">
              {fileContent}
            </pre>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-[11px] text-text-tertiary">Select a file to preview</p>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Diff pane
// ---------------------------------------------------------------------------

function DiffPane() {
  const [status, setStatus] = useState<{ branch: string; commit: string; changed_files: GitChanged[] } | null>(null)
  const [diff, setDiff] = useState('')
  const [sourceEnv, setSourceEnv] = useState('')

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/umh/workspace/git-status')
      const data = await res.json()
      if (data.ok) {
        setStatus({ branch: data.branch, commit: data.commit, changed_files: data.changed_files })
        setSourceEnv(data.source_env)
      }
    } catch { /* noop */ }
  }, [])

  usePolling(fetchStatus, 30000)

  const fetchDiff = async (path?: string) => {
    try {
      const url = path
        ? `/api/umh/workspace/git-diff-file?path=${encodeURIComponent(path)}`
        : '/api/umh/workspace/git-diff'
      const res = await fetch(url)
      const data = await res.json()
      if (data.ok) setDiff(data.diff || data.stat || 'No changes')
    } catch { /* noop */ }
  }

  return (
    <div className="flex h-full">
      {/* Changed files */}
      <div className="w-64 shrink-0 overflow-y-auto border-r border-border bg-canvas">
        <div className="px-3 py-2 border-b border-border">
          <div className="flex items-center justify-between">
            <p className="wv-label">Changes</p>
            {sourceEnv && <span className="text-[9px] font-mono text-text-tertiary">{sourceEnv}</span>}
          </div>
          {status && (
            <div className="mt-1 flex items-center gap-2">
              <span className="text-[10px] font-mono text-cyan">{status.branch}</span>
              <span className="text-[10px] font-mono text-text-tertiary">{status.commit}</span>
            </div>
          )}
        </div>
        <button
          onClick={() => fetchDiff()}
          className="w-full text-left px-3 py-1.5 text-[11px] text-cyan hover:bg-surface-raised border-b border-border"
        >
          Show full diff
        </button>
        {status?.changed_files.map((f) => (
          <button
            key={f.path}
            onClick={() => fetchDiff(f.path)}
            className="w-full text-left flex items-center gap-2 px-3 py-0.5 text-[11px] hover:bg-surface-raised"
          >
            <span className={clsx(
              'text-[10px] font-mono w-4 shrink-0',
              f.status === 'M' && 'text-warn',
              f.status === 'A' && 'text-ok',
              f.status === 'D' && 'text-danger',
              f.status === '??' && 'text-text-tertiary',
            )}>{f.status}</span>
            <span className="truncate text-text-secondary">{f.path}</span>
          </button>
        ))}
        {status && status.changed_files.length === 0 && (
          <p className="px-3 py-4 text-[11px] text-text-tertiary text-center">Clean working tree</p>
        )}
      </div>

      {/* Diff viewer */}
      <pre className="flex-1 overflow-auto p-3 font-mono text-[11px] text-text-secondary bg-surface whitespace-pre-wrap">
        {diff || 'Select a file or click "Show full diff"'}
      </pre>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Test results pane
// ---------------------------------------------------------------------------

function TestResultsPane() {
  const [results, setResults] = useState<any>(null)

  const fetchResults = useCallback(async () => {
    try {
      const res = await fetch('/api/umh/workspace/test-results')
      const data = await res.json()
      if (data.ok) setResults(data)
    } catch { /* noop */ }
  }, [])

  usePolling(fetchResults, 30000)

  if (!results) {
    return <div className="flex-1 flex items-center justify-center"><p className="text-[11px] text-text-tertiary">Loading...</p></div>
  }

  if (!results.has_results) {
    return (
      <div className="p-6">
        <p className="text-[12px] text-text-secondary mb-3">No test results available</p>
        <div className="bg-surface-secondary border border-border rounded p-3">
          <p className="wv-label mb-1">Recommended command</p>
          <code className="text-[11px] font-mono text-cyan">{results.recommended_command}</code>
        </div>
        <p className="text-[10px] text-text-tertiary mt-2">{results.message}</p>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center gap-3">
        <span className={clsx(
          'px-2 py-0.5 rounded text-[11px] font-mono',
          results.status === 'pass' ? 'bg-ok/10 text-ok' : 'bg-danger/10 text-danger',
        )}>
          {results.status?.toUpperCase()}
        </span>
        {results.source_env && <span className="text-[9px] font-mono text-text-tertiary">{results.source_env}</span>}
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-surface-secondary border border-border rounded p-2 text-center">
          <p className="text-lg font-mono text-ok">{results.passed ?? '—'}</p>
          <p className="wv-label">Passed</p>
        </div>
        <div className="bg-surface-secondary border border-border rounded p-2 text-center">
          <p className="text-lg font-mono text-danger">{results.failed ?? '—'}</p>
          <p className="wv-label">Failed</p>
        </div>
        <div className="bg-surface-secondary border border-border rounded p-2 text-center">
          <p className="text-lg font-mono text-text-tertiary">{results.skipped ?? '—'}</p>
          <p className="wv-label">Skipped</p>
        </div>
      </div>
      {results.command && (
        <div className="bg-surface-secondary border border-border rounded p-2">
          <p className="wv-label mb-1">Command</p>
          <code className="text-[11px] font-mono text-text-secondary">{results.command}</code>
        </div>
      )}
      {results.duration_seconds != null && (
        <p className="text-[10px] text-text-tertiary">Duration: {results.duration_seconds.toFixed(1)}s</p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Logs pane
// ---------------------------------------------------------------------------

function LogsPane() {
  const [logs, setLogs] = useState<any[]>([])
  const [sourceEnv, setSourceEnv] = useState('')

  const fetchLogs = useCallback(async () => {
    try {
      const res = await fetch('/api/umh/workspace/execution-logs?limit=50')
      const data = await res.json()
      if (data.ok) {
        setLogs(data.logs)
        setSourceEnv(data.source_env)
      }
    } catch { /* noop */ }
  }, [])

  usePolling(fetchLogs, 15000)

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-border bg-canvas flex items-center justify-between">
        <p className="wv-label">Execution Logs</p>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-text-tertiary">{logs.length} entries</span>
          {sourceEnv && <span className="text-[9px] font-mono text-text-tertiary">{sourceEnv}</span>}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5 font-mono text-[11px]">
        {logs.length === 0 && <p className="text-text-tertiary text-center py-4">No execution logs available</p>}
        {logs.map((log, i) => (
          <div key={i} className="flex items-start gap-2 py-0.5 hover:bg-surface-raised rounded px-1">
            <span className="text-text-tertiary shrink-0 w-36 text-[10px]">
              {log.timestamp || log.ts || '—'}
            </span>
            <span className={clsx(
              'shrink-0 w-16 text-[10px]',
              log.level === 'error' && 'text-danger',
              log.level === 'warn' && 'text-warn',
              log.status === 'failed' && 'text-danger',
            )}>
              {log.level || log.status || log.type || '—'}
            </span>
            <span className="text-text-secondary truncate">
              {log.message || log.event || log.description || JSON.stringify(log).slice(0, 120)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Proof pane
// ---------------------------------------------------------------------------

function ProofPane() {
  const [artifacts, setArtifacts] = useState<any[]>([])
  const [playwrightAvailable, setPlaywrightAvailable] = useState(false)
  const [consoleAvailable, setConsoleAvailable] = useState(false)
  const [consoleBlocker, setConsoleBlocker] = useState('')

  const fetchProof = useCallback(async () => {
    try {
      const res = await fetch('/api/umh/workspace/proof-artifacts')
      const data = await res.json()
      if (data.ok) {
        setArtifacts(data.artifacts)
        setPlaywrightAvailable(data.playwright_available)
        setConsoleAvailable(data.console_capture_available)
        setConsoleBlocker(data.console_capture_blocker || '')
      }
    } catch { /* noop */ }
  }, [])

  usePolling(fetchProof, 30000)

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-border bg-canvas">
        <p className="wv-label">Proof & Preview</p>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Capability status */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-surface-secondary border border-border rounded p-2">
            <div className="flex items-center gap-2 mb-1">
              <span className={clsx('w-2 h-2 rounded-full', playwrightAvailable ? 'bg-ok' : 'bg-danger')} />
              <span className="text-[11px] font-mono text-text-primary">Playwright</span>
            </div>
            <p className="text-[10px] text-text-tertiary">
              {playwrightAvailable ? 'Available for screenshot proof' : 'Skill present but not connected'}
            </p>
          </div>
          <div className="bg-surface-secondary border border-border rounded p-2">
            <div className="flex items-center gap-2 mb-1">
              <span className={clsx('w-2 h-2 rounded-full', consoleAvailable ? 'bg-ok' : 'bg-danger')} />
              <span className="text-[11px] font-mono text-text-primary">Console Capture</span>
            </div>
            <p className="text-[10px] text-text-tertiary">
              {consoleAvailable ? 'Available' : consoleBlocker || 'Not available'}
            </p>
          </div>
        </div>

        {/* Artifacts */}
        {artifacts.length > 0 ? (
          <div className="space-y-2">
            <p className="wv-label">{artifacts.length} proof artifact{artifacts.length !== 1 ? 's' : ''}</p>
            {artifacts.map((a, i) => (
              <div key={i} className="bg-surface-secondary border border-border rounded p-2 flex items-center gap-3">
                <span className={clsx(
                  'text-[10px] font-mono px-1.5 py-0.5 rounded',
                  a.type === 'screenshot' && 'bg-cyan/10 text-cyan',
                  a.type === 'metadata' && 'bg-warn/10 text-warn',
                  a.type === 'report' && 'bg-ok/10 text-ok',
                )}>{a.type}</span>
                <span className="text-[11px] text-text-primary truncate">{a.name}</span>
                <span className="ml-auto text-[9px] text-text-tertiary shrink-0">
                  {a.size > 1024 ? `${(a.size / 1024).toFixed(0)}K` : `${a.size}B`}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[11px] text-text-tertiary text-center py-4">No proof artifacts found</p>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Health pane
// ---------------------------------------------------------------------------

function HealthPane() {
  const [health, setHealth] = useState<any>(null)

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/umh/workspace/health')
      const data = await res.json()
      if (data.ok) setHealth(data)
    } catch { /* noop */ }
  }, [])

  usePolling(fetchHealth, 30000)

  if (!health) {
    return <div className="flex-1 flex items-center justify-center"><p className="text-[11px] text-text-tertiary">Loading...</p></div>
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-3">
        <span className={clsx(
          'px-2 py-0.5 rounded text-[11px] font-mono',
          health.overall === 'healthy' ? 'bg-ok/10 text-ok' : 'bg-warn/10 text-warn',
        )}>
          {health.overall?.toUpperCase()}
        </span>
        {health.source_env && <span className="text-[9px] font-mono text-text-tertiary">{health.source_env}</span>}
      </div>

      <div className="space-y-2">
        {health.checks?.map((c: any, i: number) => (
          <div key={i} className="bg-surface-secondary border border-border rounded p-3">
            <div className="flex items-center gap-2 mb-1">
              <span className={clsx(
                'w-2 h-2 rounded-full',
                c.status === 'reachable' && 'bg-ok',
                c.status === 'unreachable' && 'bg-danger',
                c.status === 'unconfigured' && 'bg-text-tertiary',
                c.status === 'unavailable' && 'bg-warn',
              )} />
              <span className="text-[11px] font-mono text-text-primary">{c.name}</span>
              <span className="ml-auto text-[9px] font-mono text-text-tertiary">{c.status}</span>
            </div>
            {c.error && <p className="text-[10px] text-danger mt-1">{c.error}</p>}
            {c.message && <p className="text-[10px] text-text-tertiary mt-1">{c.message}</p>}
            {c.containers && (
              <div className="mt-1.5 space-y-0.5">
                {c.containers.map((ct: any, j: number) => (
                  <div key={j} className="flex items-center gap-2 text-[10px]">
                    <span className={clsx(
                      'w-1.5 h-1.5 rounded-full',
                      ct.status?.includes('Up') ? 'bg-ok' : 'bg-danger',
                    )} />
                    <span className="font-mono text-text-secondary">{ct.name}</span>
                    <span className="text-text-tertiary">{ct.status}</span>
                  </div>
                ))}
              </div>
            )}
            {c.last_check && (
              <p className="text-[9px] text-text-tertiary mt-1">
                Last check: {new Date(c.last_check).toLocaleTimeString()}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
