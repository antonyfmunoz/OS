import { useEffect, useRef, useState } from 'react'
import {
  FolderTree, MonitorPlay, GitBranch, Database, Map, Shield,
  Terminal as TerminalIcon, Box, Cpu, X, PanelBottomOpen,
  Maximize2, Minimize2,
} from 'lucide-react'
import { useMetaIDEStore, type SidebarTab, type PanelTab } from '../stores/metaIDEStore'
import { useCollapseStore } from '../stores/collapseStore'
import { useEditorStore } from '../stores/editorStore'
import { useProviderRegistryStore } from '../stores/providerRegistryStore'
import { useViewContextStore } from '../stores/viewContextStore'
import { fetchApi } from '../api/client'
import { useBootstrapStore } from '../stores/bootstrapStore'
import { VPS, BEAST } from '../constants/devices'
import type { LucideIcon } from 'lucide-react'

const SIDEBAR_ITEMS: Array<{ id: SidebarTab; icon: LucideIcon; label: string }> = [
  { id: 'files', icon: FolderTree, label: 'FILES' },
  { id: 'sessions', icon: MonitorPlay, label: 'SESSIONS' },
  { id: 'workspace', icon: GitBranch, label: 'WORKSPACE' },
  { id: 'repositories', icon: Database, label: 'REPOSITORIES' },
  { id: 'roadmap', icon: Map, label: 'ROADMAP' },
  { id: 'risks', icon: Shield, label: 'RISKS' },
]

const PANEL_TABS: Array<{ id: PanelTab; icon: LucideIcon; label: string }> = [
  { id: 'terminal', icon: TerminalIcon, label: 'Terminal' },
  { id: 'terminals', icon: TerminalIcon, label: 'Sessions' },
  { id: 'containers', icon: Box, label: 'Containers' },
  { id: 'runtimes', icon: Cpu, label: 'Runtimes' },
]

const RISK_COLORS: Record<string, string> = {
  none: 'text-text-secondary',
  low: 'text-ok',
  medium: 'text-warn',
  high: 'text-orange-400',
  critical: 'text-danger',
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: 'text-ok',
  dirty: 'text-warn',
  stale: 'text-orange-400',
  detached: 'text-danger',
  unknown: 'text-text-tertiary',
  degraded: 'text-orange-400',
  crashed: 'text-danger',
}

const STATE_COLORS: Record<string, string> = {
  completed: 'text-ok',
  in_progress: 'text-cyan',
  planned: 'text-text-secondary',
  blocked: 'text-danger',
  unknown: 'text-text-tertiary',
}

// ─── Drag resize hook ───────────────────────────────────────────

function useDragResize(
  axis: 'x' | 'y',
  onResize: (px: number) => void,
  invert = false,
) {
  const dragging = useRef(false)
  const startPos = useRef(0)
  const startSize = useRef(0)

  const onMouseDown = (e: React.MouseEvent, currentSize: number) => {
    e.preventDefault()
    dragging.current = true
    startPos.current = axis === 'x' ? e.clientX : e.clientY
    startSize.current = currentSize
    document.body.style.cursor = axis === 'x' ? 'col-resize' : 'row-resize'
    document.body.style.userSelect = 'none'

    const onMouseMove = (ev: MouseEvent) => {
      if (!dragging.current) return
      const delta = (axis === 'x' ? ev.clientX : ev.clientY) - startPos.current
      onResize(startSize.current + (invert ? -delta : delta))
    }
    const onMouseUp = () => {
      dragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }

  return onMouseDown
}

// ─── Tab context menu ───────────────────────────────────────────

function TabContextMenu({ x, y, path, onClose }: {
  x: number; y: number; path: string; onClose: () => void
}) {
  const closeFile = useEditorStore((s) => s.closeFile)
  const closeOtherFiles = useEditorStore((s) => s.closeOtherFiles)
  const closeAllFiles = useEditorStore((s) => s.closeAllFiles)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose])

  const items = [
    { label: 'Close', action: () => closeFile(path) },
    { label: 'Close Others', action: () => closeOtherFiles(path) },
    { label: 'Close All', action: () => closeAllFiles() },
  ]

  return (
    <div
      ref={menuRef}
      className="fixed z-50 bg-surface-raised border border-border rounded shadow-lg py-1 min-w-[140px]"
      style={{ left: x, top: y }}
    >
      {items.map((item) => (
        <button
          key={item.label}
          onClick={() => { item.action(); onClose() }}
          className="w-full text-left px-3 py-1.5 text-[11px] text-text-primary hover:bg-cyan-glow hover:text-cyan transition-colors"
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}

type FileEntry = { name: string; path: string; type: 'file' | 'directory' }
type MeshNode = { id: string; name: string; os: string; status: string; ip?: string; device_type?: string }

async function browseDir(path: string, node?: string): Promise<FileEntry[]> {
  if (node === 'windows') {
    try {
      const data = await fetchApi<{ ok: boolean; entries: FileEntry[] }>(
        `/workspace/remote-browse?node=windows&path=${encodeURIComponent(path)}`,
      )
      if (data.ok && data.entries) return data.entries.map((e) => ({ name: e.name, path: e.path, type: e.type }))
    } catch { /* remote browse failed */ }
    return []
  }
  try {
    const qs = path ? `?path=${encodeURIComponent(path)}` : ''
    const data = await fetchApi<{ ok: boolean; entries: FileEntry[] }>(`/workspace/browse${qs}`)
    if (data.ok && data.entries) return data.entries.map((e) => ({ name: e.name, path: e.path, type: e.type }))
  } catch { /* API fallback failed */ }
  return []
}

function detectLang(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const map: Record<string, string> = {
    ts: 'typescript', tsx: 'typescriptreact', js: 'javascript', jsx: 'javascriptreact',
    py: 'python', md: 'markdown', json: 'json', css: 'css', html: 'html',
    yaml: 'yaml', yml: 'yaml', toml: 'toml', sql: 'sql', sh: 'shellscript',
    rs: 'rust', go: 'go', rb: 'ruby', java: 'java', c: 'c', cpp: 'cpp',
    ps1: 'powershell', bat: 'bat', cmd: 'bat', xml: 'xml', txt: 'plaintext',
  }
  return map[ext] || 'plaintext'
}

async function readFileContent(path: string, node?: string): Promise<{ content: string; name: string } | null> {
  const sep = node === 'windows' ? '\\' : '/'
  const fname = path.split(sep).pop() || path
  if (node === 'windows') {
    try {
      const data = await fetchApi<{ ok: boolean; content: string }>(`/workspace/remote-read-file?node=windows&path=${encodeURIComponent(path)}`)
      if (data.ok && data.content !== undefined) return { content: data.content, name: fname }
    } catch { /* remote read failed */ }
    return null
  }
  try {
    const content = await window.cockpit?.readFile?.(path)
    if (content !== undefined) return { content, name: fname }
  } catch { /* IPC unavailable */ }
  try {
    const data = await fetchApi<{ ok: boolean; content: string }>(`/workspace/read-file?path=${encodeURIComponent(path)}`)
    if (data.ok && data.content !== undefined) return { content: data.content, name: fname }
  } catch { /* API fallback failed */ }
  return null
}

async function writeFileContent(path: string, content: string, node?: string): Promise<boolean> {
  if (node === 'windows') {
    try {
      const data = await fetchApi<{ ok: boolean }>('/workspace/remote-write-file', {
        method: 'POST', body: JSON.stringify({ node: 'windows', path, content }),
      })
      return data.ok === true
    } catch { return false }
  }
  try {
    await window.cockpit?.writeFile?.(path, content)
    return true
  } catch { /* IPC unavailable */ }
  try {
    const data = await fetchApi<{ ok: boolean }>('/workspace/write-file', {
      method: 'POST', body: JSON.stringify({ path, content }),
    })
    return data.ok === true
  } catch { return false }
}

// ─── File tree node ──────────────────────────────────────────────

function IDEFileTreeNode({ name, path, type, depth, node, onFileOpen }: {
  name: string; path: string; type: 'file' | 'directory'; depth: number; node?: string
  onFileOpen?: (path: string, node?: string) => void
}) {
  const dirKey = `filetree:${node || 'vps'}:${path}`
  const expanded = useCollapseStore((s) => s.isOpen(dirKey))
  const toggleDir = useCollapseStore((s) => s.toggle)
  const [children, setChildren] = useState<FileEntry[]>([])
  const childrenLoaded = useRef(false)

  useEffect(() => {
    if (expanded && !childrenLoaded.current) {
      browseDir(path, node).then((entries) => { setChildren(entries); childrenLoaded.current = true })
    }
  }, [expanded, path, node])

  const handleClick = async () => {
    if (type === 'directory') {
      if (!expanded && !childrenLoaded.current) {
        const entries = await browseDir(path, node)
        setChildren(entries)
        childrenLoaded.current = true
      }
      toggleDir(dirKey)
    } else if (onFileOpen) {
      onFileOpen(path, node)
    }
  }

  return (
    <>
      <button
        onClick={handleClick}
        className={`w-full text-left flex items-center gap-1 py-0.5 hover:bg-surface-raised transition-colors text-[11px] ${
          type === 'directory' ? 'text-text-primary' : 'text-text-secondary'
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <span className="text-text-tertiary w-3 text-center text-[9px]">
          {type === 'directory' ? (expanded ? '▾' : '▸') : '·'}
        </span>
        <span className="truncate">{name}</span>
      </button>
      {expanded && children.map((child) => (
        <IDEFileTreeNode
          key={child.path}
          name={child.name}
          path={child.path}
          type={child.type}
          depth={depth + 1}
          node={node}
          onFileOpen={onFileOpen}
        />
      ))}
    </>
  )
}

// ─── Sidebar: Files ──────────────────────────────────────────────

function FilesPanel() {
  const vpsTree = useMetaIDEStore((s) => s.vpsTree)
  const windowsTree = useMetaIDEStore((s) => s.windowsTree)
  const meshNodes = useMetaIDEStore((s) => s.fileMeshNodes)
  const windowsOnline = useMetaIDEStore((s) => s.windowsOnline)
  const vpsExpanded = useCollapseStore((s) => s.isOpen('metaide:vps', true))
  const windowsExpanded = useCollapseStore((s) => s.isOpen('metaide:windows', true))
  const toggleSection = useCollapseStore((s) => s.toggle)
  const setActiveTab = useMetaIDEStore((s) => s.setActiveTab)
  const bootstrapLoaded = useBootstrapStore((s) => s.loaded)
  const [fetchFailed, setFetchFailed] = useState(false)

  const refreshData = async () => {
    const store = useMetaIDEStore.getState()
    const vpsEntries = await browseDir('/')
    if (vpsEntries.length > 0) { store.setVpsTree(vpsEntries); setFetchFailed(false) }
    else if (store.vpsTree.length === 0) setFetchFailed(true)

    browseDir('C:\\', 'windows').then((entries) => { if (entries.length > 0) store.setWindowsTree(entries) })

    try {
      const data = await fetchApi<{ ok: boolean; nodes: MeshNode[] }>('/workspace/mesh-nodes')
      if (data.ok && data.nodes) {
        store.setFileMeshNodes(data.nodes)
      }
    } catch { /* mesh-nodes unavailable */ }
  }

  useEffect(() => {
    refreshData()
    const id = setInterval(refreshData, 30000)
    return () => clearInterval(id)
  }, [])

  const openFileInEditor = async (path: string, node?: string) => {
    const result = await readFileContent(path, node)
    if (result) {
      useEditorStore.getState().openFile({
        path, name: result.name, content: result.content,
        language: detectLang(result.name), dirty: false, node,
      })
      setActiveTab('editor')
    }
  }

  const vpsName = meshNodes.find((n) => n.id === 'vps')?.name || VPS.displayName
  const windowsName = meshNodes.find((n) => n.os === 'windows')?.name || BEAST.displayName
  const windowsKnown = bootstrapLoaded || meshNodes.length > 0

  return (
    <div className="py-1">
      <button
        onClick={() => toggleSection('metaide:vps')}
        className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-surface-raised transition-colors"
      >
        <span className="text-text-tertiary text-[9px]">{vpsExpanded ? '▾' : '▸'}</span>
        <span className="text-ok text-[9px]">●</span>
        <span className="wv-label flex-1 text-left">{vpsName}</span>
      </button>
      {vpsExpanded && (
        <>
          {vpsTree.map((f) => (
            <IDEFileTreeNode key={f.path} name={f.name} path={f.path} type={f.type} depth={1} onFileOpen={openFileInEditor} />
          ))}
          {vpsTree.length === 0 && (
            <p className="text-[11px] px-4 py-2 text-text-tertiary">
              {fetchFailed ? (
                <button onClick={refreshData} className="text-cyan hover:underline">Retry — failed to load</button>
              ) : 'Loading...'}
            </p>
          )}
        </>
      )}

      <button
        onClick={() => toggleSection('metaide:windows')}
        className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-surface-raised transition-colors border-t border-border mt-1"
      >
        <span className="text-text-tertiary text-[9px]">{windowsExpanded ? '▾' : '▸'}</span>
        <span className={`text-[9px] ${windowsOnline ? 'text-ok' : 'text-text-tertiary'}`}>●</span>
        <span className="wv-label flex-1 text-left">{windowsName}</span>
      </button>
      {windowsExpanded && (
        <>
          {windowsOnline ? (
            <>
              {windowsTree.map((f) => (
                <IDEFileTreeNode key={f.path} name={f.name} path={f.path} type={f.type} depth={1} node="windows" onFileOpen={openFileInEditor} />
              ))}
              {windowsTree.length === 0 && <p className="text-[11px] px-4 py-2 text-text-tertiary">Loading files...</p>}
            </>
          ) : (
            <p className="text-[11px] px-4 py-2 text-text-tertiary">
              {windowsKnown ? 'Offline' : 'Connecting...'}
            </p>
          )}
        </>
      )}
    </div>
  )
}

// ─── Sidebar: Sessions ───────────────────────────────────────────

function SessionsPanel() {
  const sessions = useEditorStore((s) => s.sessions)
  const ccDelegating = useEditorStore((s) => s.ccDelegating)
  const fetchSessions = useEditorStore((s) => s.fetchSessions)
  const delegateToClaudeCode = useEditorStore((s) => s.delegateToClaudeCode)
  const captureSession = useEditorStore((s) => s.captureSession)
  const gitBranch = useEditorStore((s) => s.gitBranch)
  const gitChangedCount = useEditorStore((s) => s.gitChangedCount)
  const fetchGitStatus = useEditorStore((s) => s.fetchGitStatus)
  const setViewContext = useViewContextStore((s) => s.setContext)

  const [ccPrompt, setCcPrompt] = useState('')
  const [ccTarget, setCcTarget] = useState('')
  const [capturedOutput, setCapturedOutput] = useState('')

  useEffect(() => {
    fetchGitStatus()
    fetchSessions()
    const id = setInterval(() => { fetchGitStatus(); fetchSessions() }, 15000)
    return () => clearInterval(id)
  }, [fetchGitStatus, fetchSessions])

  return (
    <div className="p-3 space-y-3">
      {gitBranch && (
        <div className="border border-border rounded p-2">
          <div className="wv-label mb-1">Git</div>
          <div className="text-xs text-cyan font-mono">
            {gitBranch}{gitChangedCount > 0 ? <span className="text-warn ml-2">+{gitChangedCount}</span> : ''}
          </div>
        </div>
      )}

      <div>
        <div className="wv-label mb-2">Active Sessions</div>
        {sessions.length === 0 && <p className="text-xs text-text-tertiary text-center py-3">No active sessions</p>}
        {sessions.map((s) => (
          <div key={s.name} className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-surface-raised text-xs border border-border mb-1">
            <span className={`w-2 h-2 rounded-full ${s.status === 'active' ? 'bg-ok' : 'bg-text-tertiary'}`} />
            <span className="text-text-primary flex-1 truncate font-mono text-[10px]">{s.name}</span>
            <span className="text-[8px] text-text-tertiary uppercase">{s.type}</span>
            <button
              onClick={async () => {
                const output = await captureSession(s.name)
                setCapturedOutput(output)
                setViewContext({ selected_object_type: 'session', selected_session_id: s.name })
              }}
              className="text-[9px] text-cyan hover:underline"
            >
              capture
            </button>
          </div>
        ))}
      </div>

      <div className="border border-border rounded p-2">
        <div className="wv-label mb-2">Delegate to Claude Code</div>
        <select
          value={ccTarget}
          onChange={(e) => setCcTarget(e.target.value)}
          className="w-full mb-2 text-[10px] bg-surface-raised border border-border rounded px-2 py-1 text-text-primary"
        >
          <option value="">Select session...</option>
          {sessions.map((s) => (
            <option key={s.name} value={s.name}>{s.name}</option>
          ))}
        </select>
        <textarea
          value={ccPrompt}
          onChange={(e) => setCcPrompt(e.target.value)}
          placeholder="Enter prompt..."
          className="w-full text-[10px] bg-surface-raised border border-border rounded px-2 py-1 text-text-primary placeholder-text-tertiary resize-none h-16"
        />
        <button
          onClick={async () => {
            if (ccTarget && ccPrompt.trim()) {
              await delegateToClaudeCode(ccTarget, ccPrompt)
              setCcPrompt('')
            }
          }}
          disabled={!ccTarget || !ccPrompt.trim() || ccDelegating}
          className="mt-1.5 w-full text-[10px] px-2 py-1 bg-cyan-glow text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-30 font-mono uppercase tracking-wider"
        >
          {ccDelegating ? 'Sending...' : 'Send Prompt'}
        </button>
      </div>

      {capturedOutput && (
        <div className="border border-border rounded p-2">
          <div className="wv-label mb-1">Captured Output</div>
          <pre className="text-[9px] font-mono text-text-secondary bg-surface p-2 rounded max-h-32 overflow-y-auto whitespace-pre-wrap">
            {capturedOutput}
          </pre>
        </div>
      )}
    </div>
  )
}

// ─── Sidebar: Workspace ──────────────────────────────────────────

function WorkspacePanel() {
  const { workspace, fetchWorkspace, loading } = useMetaIDEStore()

  useEffect(() => { fetchWorkspace() }, [])

  if (loading && !workspace) return <div className="p-3 text-text-tertiary text-xs">Loading workspace...</div>
  if (!workspace) return <div className="p-3 text-text-tertiary text-xs">No workspace data</div>

  return (
    <div className="p-3 space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="Dirty" value={workspace.totals.dirty_files} warn={workspace.totals.dirty_files > 0} />
        <StatCard label="Branches" value={workspace.totals.branches} />
        <StatCard label="Worktrees" value={workspace.totals.worktrees} />
        <StatCard label="Stale" value={workspace.totals.stale_branches} warn={workspace.totals.stale_branches > 0} />
      </div>

      <div className="border border-border rounded p-2">
        <div className="wv-label mb-1">Risk</div>
        <div className={`text-sm font-bold ${RISK_COLORS[workspace.overall_risk] || 'text-text-secondary'}`}>
          {workspace.overall_risk.toUpperCase()}
        </div>
      </div>

      {workspace.repos.map((repo) => (
        <div key={repo.path} className="border border-border rounded p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-text-primary">{repo.name}</span>
            <span className={`text-[10px] ${HEALTH_COLORS[repo.health] || 'text-text-tertiary'}`}>{repo.health}</span>
          </div>
          <div className="text-[10px] text-text-secondary">
            <span className="text-text-primary">{repo.branch}</span> · {repo.dirty}D {repo.staged}S {repo.branches}B {repo.worktrees}W
          </div>
          {repo.issues.length > 0 && <div className="text-[10px] text-warn mt-1">{repo.issues.join(' · ')}</div>}
        </div>
      ))}
    </div>
  )
}

// ─── Sidebar: Repositories ───────────────────────────────────────

function RepositoriesPanel() {
  const { repositories, fetchRepositories, loading } = useMetaIDEStore()

  useEffect(() => { fetchRepositories() }, [])

  if (loading && repositories.length === 0) return <div className="p-3 text-text-tertiary text-xs">Loading...</div>
  if (repositories.length === 0) return <div className="p-3 text-text-tertiary text-xs">No repositories</div>

  return (
    <div className="p-3 space-y-3">
      {repositories.map((repo) => (
        <div key={repo.repo_path} className="border border-border rounded p-2 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-text-primary">{repo.repo_name}</span>
            <span className={`text-[10px] ${HEALTH_COLORS[repo.health.status]}`}>{repo.health.status}</span>
          </div>
          <div className="text-[10px] text-text-secondary">
            <span className="text-text-primary">{repo.current_branch}</span> @ {repo.head_commit.slice(0, 8)}
          </div>
          {repo.dirty_files.length > 0 && (
            <div className="text-[10px]">
              <div className="text-warn mb-0.5">Dirty ({repo.dirty_files.length})</div>
              <div className="max-h-20 overflow-y-auto space-y-0.5">
                {repo.dirty_files.slice(0, 8).map((f) => (
                  <div key={f} className="text-text-tertiary font-mono truncate">{f}</div>
                ))}
                {repo.dirty_files.length > 8 && <div className="text-text-tertiary">+{repo.dirty_files.length - 8} more</div>}
              </div>
            </div>
          )}
          {repo.worktrees.length > 1 && (
            <div className="text-[10px]">
              <div className="text-cyan mb-0.5">Worktrees ({repo.worktrees.length})</div>
              {repo.worktrees.map((w) => (
                <div key={w.path} className="flex items-center gap-2 text-text-tertiary">
                  <span className="font-mono truncate flex-1">{w.branch || '(detached)'}</span>
                  {w.locked && <span className="text-warn text-[9px]">LOCKED</span>}
                  {w.detached && <span className="text-danger text-[9px]">DETACHED</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ─── Sidebar: Roadmap ────────────────────────────────────────────

function RoadmapPanel() {
  const { roadmap, fetchRoadmap, loading } = useMetaIDEStore()

  useEffect(() => { fetchRoadmap() }, [])

  if (loading && !roadmap) return <div className="p-3 text-text-tertiary text-xs">Loading roadmap...</div>
  if (!roadmap) return <div className="p-3 text-text-tertiary text-xs">No roadmap data</div>

  return (
    <div className="p-3 space-y-3">
      <div className="border border-border rounded p-2">
        <div className="wv-label mb-1">Progress</div>
        <div className="h-1.5 bg-surface-raised rounded overflow-hidden">
          <div className="h-full bg-ok rounded" style={{ width: `${Math.round(roadmap.completion_ratio * 100)}%` }} />
        </div>
        <div className="text-[10px] text-text-secondary mt-1">{Math.round(roadmap.completion_ratio * 100)}% · {roadmap.completed_phases.length}/{roadmap.total_phases}</div>
      </div>

      {roadmap.current_phase && (
        <div className="border border-cyan/30 rounded p-2">
          <div className="wv-label text-cyan mb-1">Current</div>
          <div className="text-xs text-text-primary">P{roadmap.current_phase.phase_number}: {roadmap.current_phase.phase_name}</div>
        </div>
      )}

      {roadmap.completed_phases.length > 0 && (
        <div>
          <div className="wv-label mb-1">Completed ({roadmap.completed_phases.length})</div>
          <div className="space-y-0.5 max-h-40 overflow-y-auto">
            {roadmap.completed_phases.map((p) => <PhaseRow key={p.phase_number} phase={p} />)}
          </div>
        </div>
      )}

      {roadmap.planned_phases.length > 0 && (
        <div>
          <div className="wv-label mb-1">Planned ({roadmap.planned_phases.length})</div>
          <div className="space-y-0.5">
            {roadmap.planned_phases.map((p) => <PhaseRow key={p.phase_number} phase={p} />)}
          </div>
        </div>
      )}

      {roadmap.blocked_phases.length > 0 && (
        <div>
          <div className="wv-label text-danger mb-1">Blocked ({roadmap.blocked_phases.length})</div>
          <div className="space-y-0.5">
            {roadmap.blocked_phases.map((p) => <PhaseRow key={p.phase_number} phase={p} />)}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Sidebar: Risks ──────────────────────────────────────────────

function RisksPanel() {
  const { risks, overallRisk, fetchRisks, loading } = useMetaIDEStore()

  useEffect(() => { fetchRisks() }, [])

  if (loading && risks.length === 0) return <div className="p-3 text-text-tertiary text-xs">Loading risks...</div>

  return (
    <div className="p-3 space-y-3">
      <div className="border border-border rounded p-2 flex items-center justify-between">
        <span className="wv-label">Overall</span>
        <span className={`text-xs font-bold ${RISK_COLORS[overallRisk] || 'text-text-secondary'}`}>{overallRisk.toUpperCase()}</span>
      </div>
      {risks.length === 0 ? (
        <div className="text-text-tertiary text-xs text-center py-3">No risks detected</div>
      ) : (
        <div className="space-y-2">
          {risks.map((r) => (
            <div key={r.id} className="border border-border rounded p-2">
              <div className="flex items-center justify-between mb-0.5">
                <span className={`text-[10px] font-medium ${RISK_COLORS[r.level]}`}>{r.level.toUpperCase()}</span>
                <span className="text-[9px] text-text-tertiary">{r.category}</span>
              </div>
              <div className="text-xs text-text-primary">{r.description}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Center: Code Editor ─────────────────────────────────────────

function EditorContent() {
  const openFiles = useEditorStore((s) => s.openFiles)
  const activeFile = useEditorStore((s) => s.activeFile)
  const updateContent = useEditorStore((s) => s.updateContent)
  const gitBranch = useEditorStore((s) => s.gitBranch)
  const activeNode = useEditorStore((s) => s.activeNode)
  const setViewContext = useViewContextStore((s) => s.setContext)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (activeFile) {
      setViewContext({
        selected_object_type: 'file',
        selected_path: activeFile,
        selected_node: activeNode,
        selected_branch: gitBranch,
      })
    }
  }, [activeFile, activeNode, gitBranch, setViewContext])

  const activeContent = openFiles.find((f) => f.path === activeFile)

  const handleKeyDown = async (e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.key === 's' && activeFile) {
      e.preventDefault()
      const file = openFiles.find((f) => f.path === activeFile)
      if (!file) return
      const ok = await writeFileContent(file.path, file.content, file.node)
      if (ok) useEditorStore.getState().markClean(file.path)
    }
  }

  if (openFiles.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-surface">
        <div className="text-center">
          <p className="font-mono text-lg mb-2 text-cyan">META IDE</p>
          <p className="text-[10px] text-text-tertiary">Open a file from the sidebar to begin editing</p>
          <p className="text-[10px] mt-1 text-text-tertiary">
            Ctrl+S to save{gitBranch && ` · ${gitBranch}`}
          </p>
        </div>
      </div>
    )
  }

  if (!activeContent) {
    return <div className="flex-1 flex items-center justify-center text-text-tertiary text-xs bg-surface">Select a file tab</div>
  }

  return (
    <div className="flex-1 relative overflow-hidden bg-surface" onKeyDown={handleKeyDown}>
      <div className="absolute inset-0 flex">
        <div className="shrink-0 text-right pr-2 pt-2 font-mono text-[10px] select-none overflow-hidden w-12 text-text-tertiary bg-surface">
          {activeContent.content.split('\n').map((_, i) => (
            <div key={i} className="h-5">{i + 1}</div>
          ))}
        </div>
        <textarea
          ref={textareaRef}
          value={activeContent.content}
          onChange={(e) => updateContent(activeContent.path, e.target.value)}
          spellCheck={false}
          className="flex-1 resize-none p-2 font-mono text-xs text-text-primary bg-surface outline-none"
          style={{ lineHeight: '1.25rem', tabSize: 2, caretColor: 'var(--color-cyan)' }}
        />
      </div>
    </div>
  )
}

// ─── Center: Terminals ───────────────────────────────────────────

function TerminalsContent() {
  const { observation, fetchObservation, loading } = useMetaIDEStore()

  useEffect(() => { fetchObservation() }, [])

  const terminals = observation?.terminals || []
  if (loading && terminals.length === 0) return <div className="p-4 text-text-tertiary text-xs">Loading terminals...</div>
  if (terminals.length === 0) return <div className="p-4 text-text-tertiary text-xs">No active terminals</div>

  return (
    <div className="p-4 space-y-2">
      {terminals.map((t) => (
        <div key={t.terminal_id} className="border border-border rounded p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-text-primary">{t.session_name}</span>
            <span className={`text-xs ${t.is_active ? 'text-ok' : 'text-text-tertiary'}`}>
              {t.is_active ? '● active' : '○ idle'}
            </span>
          </div>
          <div className="text-xs text-text-secondary space-y-0.5">
            <div>Window: <span className="text-text-primary">{t.window_name || '—'}</span> Pane: {t.pane_index}</div>
            {t.current_command && <div>Command: <span className="text-cyan font-mono">{t.current_command}</span></div>}
            {t.cwd && <div className="text-text-tertiary font-mono truncate">{t.cwd}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Center: Containers ──────────────────────────────────────────

function ContainersContent() {
  const { observation, fetchObservation, loading } = useMetaIDEStore()

  useEffect(() => { fetchObservation() }, [])

  const containers = observation?.containers || []
  if (loading && containers.length === 0) return <div className="p-4 text-text-tertiary text-xs">Loading containers...</div>
  if (containers.length === 0) return <div className="p-4 text-text-tertiary text-xs">No containers found</div>

  return (
    <div className="p-4 space-y-2">
      {containers.map((c) => (
        <div key={c.container_id} className="border border-border rounded p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-text-primary">{c.container_name}</span>
            <span className={`text-xs ${HEALTH_COLORS[c.health] || 'text-text-tertiary'}`}>● {c.health}</span>
          </div>
          <div className="text-xs text-text-secondary space-y-0.5">
            <div>Image: <span className="text-text-secondary font-mono">{c.image}</span></div>
            <div>Status: <span className="text-text-primary">{c.status}</span></div>
            {c.ports.length > 0 && <div>Ports: <span className="text-cyan">{c.ports.join(', ')}</span></div>}
            {c.restart_count > 0 && <div className="text-warn">Restarts: {c.restart_count}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Center: Runtimes (Provider Registry) ────────────────────────

const STATUS_BADGE: Record<string, { color: string; label: string }> = {
  operational: { color: 'bg-ok', label: 'OK' },
  configured: { color: 'bg-cyan', label: 'CFG' },
  not_configured: { color: 'bg-text-tertiary', label: 'N/A' },
  error: { color: 'bg-danger', label: 'ERR' },
  unknown: { color: 'bg-text-tertiary', label: '?' },
}

function RuntimesContent() {
  const providers = useProviderRegistryStore((s) => s.providers)
  const fetchProviders = useProviderRegistryStore((s) => s.fetchProviders)
  const smokeTest = useProviderRegistryStore((s) => s.smokeTest)
  const [testResult, setTestResult] = useState<Record<string, string>>({})

  useEffect(() => { fetchProviders() }, [fetchProviders])

  const runSmoke = async (id: string) => {
    setTestResult((p) => ({ ...p, [id]: 'testing...' }))
    const res = await smokeTest(id)
    setTestResult((p) => ({ ...p, [id]: res.success ? 'pass' : res.detail }))
  }

  return (
    <div className="p-4 space-y-2">
      <div className="flex items-center justify-between mb-2">
        <span className="wv-label">Provider Registry</span>
        <button onClick={fetchProviders} className="text-[10px] text-cyan font-mono hover:underline">refresh</button>
      </div>
      {providers.map((p) => {
        const badge = STATUS_BADGE[p.status] || STATUS_BADGE.unknown
        return (
          <div key={p.id} className="border border-border rounded p-3">
            <div className="flex items-center gap-2 mb-1">
              <span className={`w-2 h-2 rounded-full shrink-0 ${badge.color}`} />
              <span className="text-xs font-medium text-text-primary">{p.name}</span>
              <span className="text-[9px] font-mono text-text-tertiary">{p.type}</span>
              <span className="ml-auto text-[9px] font-mono text-text-tertiary">{badge.label}</span>
            </div>
            <div className="flex flex-wrap gap-1 mb-2">
              {p.capabilities.map((c) => (
                <span key={c} className="px-1 py-0.5 text-[9px] rounded bg-surface-raised text-text-secondary">{c}</span>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => runSmoke(p.id)} className="px-2 py-1 text-[10px] rounded text-cyan border border-border hover:bg-cyan-glow">
                smoke test
              </button>
              {testResult[p.id] && (
                <span className={`text-[10px] font-mono ${testResult[p.id] === 'pass' ? 'text-ok' : testResult[p.id] === 'testing...' ? 'text-text-tertiary' : 'text-danger'}`}>
                  {testResult[p.id]}
                </span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Center: Previews ────────────────────────────────────────────

function PreviewsContent() {
  const { observation, fetchObservation, loading } = useMetaIDEStore()

  useEffect(() => { fetchObservation() }, [])

  const previews = observation?.previews || []
  if (loading && previews.length === 0) return <div className="p-4 text-text-tertiary text-xs">Loading previews...</div>
  if (previews.length === 0) return <div className="p-4 text-text-tertiary text-xs">No dev servers detected</div>

  return (
    <div className="p-4 space-y-2">
      {previews.map((p) => (
        <div key={p.preview_id} className="border border-border rounded p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-text-primary">{p.name}</span>
            <span className={`text-xs ${HEALTH_COLORS[p.health] || 'text-text-tertiary'}`}>● {p.health}</span>
          </div>
          <div className="text-xs text-text-secondary space-y-0.5">
            <div>URL: <span className="text-cyan font-mono">{p.url}</span></div>
            <div>Port: {p.port} | Process: <span className="text-text-primary">{p.process_name || '—'}</span></div>
            {p.restart_count > 0 && <div className="text-warn">Restarts: {p.restart_count}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Bottom: Terminal Bridge ─────────────────────────────────────

function TerminalBridge() {
  const [cmd, setCmd] = useState('')
  const [output, setOutput] = useState<string[]>([])
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight) }, [output])

  const send = async () => {
    const text = cmd.trim()
    if (!text) return
    setOutput((p) => [...p, `$ ${text}`])
    setCmd('')
    setSending(true)
    try {
      const res = await fetchApi<{ ok?: boolean; output?: string; error?: string }>('/tmux/send', {
        method: 'POST',
        body: JSON.stringify({ session_name: 'main', text }),
      })
      if (res.error) {
        setOutput((p) => [...p, `err: ${res.error}`])
      } else {
        await new Promise((r) => setTimeout(r, 1500))
        try {
          const cap = await fetchApi<{ output?: string; content?: string }>('/claude-session/capture', {
            method: 'POST',
            body: JSON.stringify({ session_name: 'main' }),
          })
          const out = cap.output || cap.content || '(no output captured)'
          setOutput((p) => [...p, out])
        } catch { setOutput((p) => [...p, '(capture failed)']) }
      }
    } catch (e) {
      setOutput((p) => [...p, `err: ${e instanceof Error ? e.message : 'send failed'}`])
    }
    setSending(false)
  }

  return (
    <div className="h-full flex flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 font-mono text-[10px] text-text-secondary">
        {output.length === 0 && <p className="text-text-tertiary">Commands run via governed tmux bridge</p>}
        {output.map((line, i) => (
          <pre key={i} className={`whitespace-pre-wrap ${line.startsWith('$') ? 'text-cyan' : line.startsWith('err:') ? 'text-danger' : ''}`}>{line}</pre>
        ))}
      </div>
      <div className="flex items-center gap-1 px-3 py-2 border-t border-border">
        <span className="text-cyan text-[10px] font-mono">$</span>
        <input
          value={cmd}
          onChange={(e) => setCmd(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder="command..."
          disabled={sending}
          className="flex-1 text-[10px] font-mono px-2 py-1 bg-surface-raised border border-border rounded outline-none placeholder:text-text-tertiary text-text-primary"
        />
        <button onClick={send} disabled={sending || !cmd.trim()} className="text-[10px] font-mono px-2 py-1 text-cyan border border-border rounded hover:bg-cyan-glow disabled:opacity-30">
          {sending ? '...' : 'Run'}
        </button>
      </div>
    </div>
  )
}

// ─── Shared ──────────────────────────────────────────────────────

function StatCard({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className="border border-border rounded p-2">
      <div className="wv-label mb-0.5">{label}</div>
      <div className={`text-sm font-bold ${warn ? 'text-warn' : 'text-text-primary'}`}>{value}</div>
    </div>
  )
}

function PhaseRow({ phase }: { phase: { phase_number: string; phase_name: string; state: string } }) {
  return (
    <div className="flex items-center gap-2 text-[10px]">
      <span className={`${STATE_COLORS[phase.state] || 'text-text-tertiary'}`}>●</span>
      <span className="text-text-secondary w-7">P{phase.phase_number}</span>
      <span className="text-text-primary truncate flex-1">{phase.phase_name}</span>
    </div>
  )
}

// ─── Right Preview Sidebar ───────────────────────────────────────

function PreviewSidebar() {
  return (
    <div className="flex-1 flex flex-col">
      <div className="flex items-center h-8 px-3 shrink-0 border-b border-border">
        <span className="wv-label text-[10px] text-cyan">Preview</span>
      </div>
      <PreviewsContent />
    </div>
  )
}

// ─── File tab with dirty indicator + middle-click ───────────────

function FileTab({ file, isActive, onActivate, onClose, onContextMenu }: {
  file: { path: string; name: string; dirty: boolean }
  isActive: boolean
  onActivate: () => void
  onClose: () => void
  onContextMenu: (e: React.MouseEvent) => void
}) {
  const [hovered, setHovered] = useState(false)

  return (
    <button
      onClick={onActivate}
      onMouseDown={(e) => { if (e.button === 1) { e.preventDefault(); onClose() } }}
      onContextMenu={onContextMenu}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`flex items-center gap-1.5 px-3 h-full text-[11px] shrink-0 border-r border-border transition-colors ${
        isActive ? 'text-text-primary bg-surface-raised' : 'text-text-tertiary hover:text-text-secondary'
      }`}
    >
      <span className="truncate max-w-[120px]">{file.name}</span>
      <span
        onClick={(e) => { e.stopPropagation(); onClose() }}
        className="ml-0.5 w-4 text-center text-[10px]"
      >
        {file.dirty && !hovered
          ? <span className="text-warn text-[9px]">●</span>
          : <span className="text-text-tertiary hover:text-text-primary">×</span>
        }
      </span>
    </button>
  )
}

// ─── Main: Meta IDE Panel ────────────────────────────────────────

export function MetaIDEPanel() {
  const {
    activeSidebar, showSidebar, toggleSidebarTab,
    activePanel, setActivePanel, showPanel, setShowPanel, togglePanel,
    panelMaximized, togglePanelMaximized,
    panelHeight, setPanelHeight,
  } = useMetaIDEStore()
  const openFiles = useEditorStore((s) => s.openFiles)
  const activeFile = useEditorStore((s) => s.activeFile)
  const setActiveFile = useEditorStore((s) => s.setActiveFile)
  const closeFile = useEditorStore((s) => s.closeFile)
  const showPreview = useEditorStore((s) => s.showPreview)
  const togglePreview = useEditorStore((s) => s.togglePreview)

  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; path: string } | null>(null)

  const panelDrag = useDragResize('y', setPanelHeight, true)

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'b') {
        e.preventDefault()
        useMetaIDEStore.getState().setShowSidebar(!useMetaIDEStore.getState().showSidebar)
      }
      if (e.ctrlKey && e.key === '`') {
        e.preventDefault()
        togglePanel()
      }
      if (e.ctrlKey && e.key === 'w') {
        e.preventDefault()
        const af = useEditorStore.getState().activeFile
        if (af) useEditorStore.getState().closeFile(af)
      }
      if (e.ctrlKey && e.key === 'Tab') {
        e.preventDefault()
        const { openFiles: files, activeFile: current } = useEditorStore.getState()
        if (files.length < 2) return
        const idx = files.findIndex((f) => f.path === current)
        const next = files[(idx + 1) % files.length]
        useEditorStore.getState().setActiveFile(next.path)
      }
      if (e.ctrlKey && e.key === '\\') {
        e.preventDefault()
        useEditorStore.getState().togglePreview()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [togglePanel])

  return (
    <div className="h-full flex overflow-hidden bg-surface">
      {/* ── Activity Bar ── */}
      <div className="w-10 shrink-0 flex flex-col items-center pt-[12px] pb-2 border-r border-border">
        {SIDEBAR_ITEMS.map(({ id, icon: Icon }) => (
          <button
            key={id}
            onClick={() => toggleSidebarTab(id)}
            className={`p-2 mt-1 transition-colors ${
              activeSidebar === id && showSidebar
                ? 'text-cyan'
                : 'text-text-tertiary hover:text-text-secondary'
            }`}
            title={id}
          >
            <Icon size={14} />
          </button>
        ))}

        <div className="flex-1" />

        <button
          onClick={togglePanel}
          className={`p-2 transition-colors ${
            showPanel ? 'text-cyan' : 'text-text-tertiary hover:text-text-secondary'
          }`}
          title="Toggle Panel (Ctrl+`)"
        >
          <PanelBottomOpen size={14} />
        </button>
      </div>

      {/* ── Left Sidebar ── */}
      {showSidebar && (
        <>
          <div className="shrink-0 flex flex-col border-r border-border overflow-hidden" style={{ width: 'var(--spacing-rail)' }}>
            <div className="flex items-center px-3 h-8 border-b border-border shrink-0">
              <span className="wv-label">{SIDEBAR_ITEMS.find((s) => s.id === activeSidebar)?.label || ''}</span>
            </div>
            <div className="flex-1 overflow-y-auto">
              {activeSidebar === 'files' && <FilesPanel />}
              {activeSidebar === 'sessions' && <SessionsPanel />}
              {activeSidebar === 'workspace' && <WorkspacePanel />}
              {activeSidebar === 'repositories' && <RepositoriesPanel />}
              {activeSidebar === 'roadmap' && <RoadmapPanel />}
              {activeSidebar === 'risks' && <RisksPanel />}
            </div>
          </div>
        </>
      )}

      {/* ── Center + Panel ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Editor tab bar — file tabs + preview toggle */}
        {!panelMaximized && (
          <div className="flex items-center h-8 shrink-0 border-b border-border overflow-x-auto">
            {openFiles.map((file) => (
              <FileTab
                key={file.path}
                file={file}
                isActive={activeFile === file.path}
                onActivate={() => setActiveFile(file.path)}
                onClose={() => closeFile(file.path)}
                onContextMenu={(e) => {
                  e.preventDefault()
                  setContextMenu({ x: e.clientX, y: e.clientY, path: file.path })
                }}
              />
            ))}
            <div className="flex-1" />
            <button
              onClick={togglePreview}
              className={`px-2 h-full text-xs transition-colors ${showPreview ? 'text-cyan' : 'text-text-tertiary hover:text-text-secondary'}`}
              title="Toggle Preview (Ctrl+\)"
            >
              ⊞
            </button>
          </div>
        )}

        {/* Editor + optional right preview split */}
        {!panelMaximized && (
          <div className="flex-1 flex min-h-0 overflow-hidden">
            <div className={`${showPreview ? 'w-1/2' : 'flex-1'} overflow-hidden`}>
              <EditorContent />
            </div>
            {showPreview && (
              <div className="w-1/2 shrink-0 flex flex-col border-l border-border">
                <PreviewSidebar />
              </div>
            )}
          </div>
        )}

        {/* ── Bottom Panel ── */}
        {showPanel && (
          <>
            {/* Panel resize handle */}
            {!panelMaximized && (
              <div
                className="h-1 shrink-0 cursor-row-resize hover:bg-cyan/30 active:bg-cyan/50 transition-colors border-t border-border"
                onMouseDown={(e) => panelDrag(e, panelHeight)}
              />
            )}
            <div
              className={`shrink-0 flex flex-col ${panelMaximized ? 'flex-1' : ''}`}
              style={panelMaximized ? undefined : { height: panelHeight }}
            >
              <div className="flex items-center h-7 shrink-0 border-b border-border px-1">
                {PANEL_TABS.map(({ id, icon: Icon, label }) => (
                  <button
                    key={id}
                    onClick={() => setActivePanel(id)}
                    className={`flex items-center gap-1 px-2 h-full text-[10px] transition-colors ${
                      activePanel === id
                        ? 'text-cyan border-b border-cyan'
                        : 'text-text-tertiary hover:text-text-secondary'
                    }`}
                  >
                    <Icon size={12} />
                    <span>{label}</span>
                  </button>
                ))}
                <div className="flex-1" />
                <button
                  onClick={togglePanelMaximized}
                  className="p-1 text-text-tertiary hover:text-text-primary transition-colors"
                  title={panelMaximized ? 'Restore Panel' : 'Maximize Panel'}
                >
                  {panelMaximized ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
                </button>
                <button
                  onClick={() => setShowPanel(false)}
                  className="p-1 text-text-tertiary hover:text-text-primary transition-colors"
                  title="Close Panel"
                >
                  <X size={12} />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto">
                {activePanel === 'terminal' && <TerminalBridge />}
                {activePanel === 'terminals' && <TerminalsContent />}
                {activePanel === 'containers' && <ContainersContent />}
                {activePanel === 'runtimes' && <RuntimesContent />}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Tab context menu */}
      {contextMenu && (
        <TabContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          path={contextMenu.path}
          onClose={() => setContextMenu(null)}
        />
      )}
    </div>
  )
}
