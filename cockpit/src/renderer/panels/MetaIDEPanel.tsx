import { useEffect, useState, useCallback } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useMetaIDEStore } from '../stores/metaIDEStore'
import { fetchApi } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { VPS, BEAST } from '../constants/devices'

const TABS = ['files', 'workspace', 'repositories', 'roadmap', 'risks', 'terminals', 'containers', 'previews'] as const

const RISK_COLORS: Record<string, string> = {
  none: 'text-zinc-400',
  low: 'text-green-400',
  medium: 'text-amber-400',
  high: 'text-orange-400',
  critical: 'text-red-400',
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: 'text-green-400',
  dirty: 'text-amber-400',
  stale: 'text-orange-400',
  detached: 'text-red-400',
  unknown: 'text-zinc-500',
  degraded: 'text-orange-400',
  crashed: 'text-red-400',
}

const STATE_COLORS: Record<string, string> = {
  completed: 'text-green-400',
  in_progress: 'text-cyan-400',
  planned: 'text-zinc-400',
  blocked: 'text-red-400',
  unknown: 'text-zinc-500',
}

type FileEntry = { name: string; path: string; type: 'file' | 'directory' }

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

function IDEFileTreeNode({ name, path, type, depth, node }: {
  name: string; path: string; type: 'file' | 'directory'; depth: number; node?: string
}) {
  const [expanded, setExpanded] = useState(false)
  const [children, setChildren] = useState<FileEntry[]>([])

  const handleClick = async () => {
    if (type === 'directory') {
      if (!expanded) setChildren(await browseDir(path, node))
      setExpanded(!expanded)
    }
  }

  return (
    <>
      <button
        onClick={handleClick}
        className={`w-full text-left flex items-center gap-1 py-0.5 hover:bg-zinc-800 transition-colors text-[11px] ${
          type === 'directory' ? 'text-zinc-200' : 'text-zinc-400'
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <span className="text-zinc-500 w-3 text-center text-[9px]">
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
        />
      ))}
    </>
  )
}

interface MeshNode { id: string; name: string; os: string; status: string }

function FilesTab() {
  const [vpsTree, setVpsTree] = useState<FileEntry[]>([])
  const [windowsTree, setWindowsTree] = useState<FileEntry[]>([])
  const [vpsExpanded, setVpsExpanded] = useState(true)
  const [windowsExpanded, setWindowsExpanded] = useState(true)
  const [meshNodes, setMeshNodes] = useState<MeshNode[]>([])
  const [windowsOnline, setWindowsOnline] = useState(false)

  useEffect(() => {
    browseDir('/').then((entries) => { if (entries.length) setVpsTree(entries) })
    browseDir('C:\\', 'windows').then((entries) => { if (entries.length) setWindowsTree(entries) })

    fetchApi<{ ok: boolean; nodes: MeshNode[] }>('/workspace/mesh-nodes')
      .then((data) => {
        if (data.ok && data.nodes) {
          setMeshNodes(data.nodes)
          setWindowsOnline(data.nodes.some((n) => n.os === 'windows' && (n.status === 'connected' || n.status === 'online')))
        }
      })
      .catch(() => {})
  }, [])

  const vpsName = meshNodes.find((n) => n.id === 'vps')?.name || VPS.displayName
  const windowsName = meshNodes.find((n) => n.os === 'windows')?.name || BEAST.displayName

  return (
    <div className="py-1">
      <button
        onClick={() => setVpsExpanded(!vpsExpanded)}
        className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-zinc-800 transition-colors"
      >
        <span className="text-zinc-500 text-[9px]">{vpsExpanded ? '▾' : '▸'}</span>
        <span className="text-green-400 text-[9px]">●</span>
        <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider flex-1 text-left">{vpsName}</span>
      </button>
      {vpsExpanded && (
        <>
          {vpsTree.map((f) => (
            <IDEFileTreeNode key={f.path} name={f.name} path={f.path} type={f.type} depth={1} />
          ))}
          {vpsTree.length === 0 && <p className="text-[11px] px-4 py-2 text-zinc-600">Loading...</p>}
        </>
      )}

      <button
        onClick={() => setWindowsExpanded(!windowsExpanded)}
        className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-zinc-800 transition-colors border-t border-zinc-800 mt-1"
      >
        <span className="text-zinc-500 text-[9px]">{windowsExpanded ? '▾' : '▸'}</span>
        <span className={`text-[9px] ${windowsOnline ? 'text-green-400' : 'text-zinc-600'}`}>●</span>
        <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider flex-1 text-left">{windowsName}</span>
        {!windowsOnline && <span className="text-[9px] text-zinc-600">offline</span>}
      </button>
      {windowsExpanded && (
        <>
          {windowsOnline ? (
            <>
              {windowsTree.map((f) => (
                <IDEFileTreeNode key={f.path} name={f.name} path={f.path} type={f.type} depth={1} node="windows" />
              ))}
              {windowsTree.length === 0 && <p className="text-[11px] px-4 py-2 text-zinc-600">Loading files...</p>}
            </>
          ) : (
            <p className="text-[11px] px-4 py-2 text-zinc-600">Device offline — connect to view files</p>
          )}
        </>
      )}
    </div>
  )
}

function WorkspaceTab() {
  const { workspace, fetchWorkspace, loading } = useMetaIDEStore()

  useEffect(() => { fetchWorkspace() }, [])

  if (loading && !workspace) return <div className="p-4 text-zinc-500">Loading workspace...</div>
  if (!workspace) return <div className="p-4 text-zinc-500">No workspace data</div>

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Dirty Files" value={workspace.totals.dirty_files} warn={workspace.totals.dirty_files > 0} />
        <StatCard label="Branches" value={workspace.totals.branches} />
        <StatCard label="Worktrees" value={workspace.totals.worktrees} />
        <StatCard label="Stale Branches" value={workspace.totals.stale_branches} warn={workspace.totals.stale_branches > 0} />
        <StatCard label="Detached WTs" value={workspace.totals.detached_worktrees} warn={workspace.totals.detached_worktrees > 0} />
        <div className="border border-zinc-700 rounded p-3">
          <div className="text-xs text-zinc-500 mb-1">Overall Risk</div>
          <div className={`text-lg font-bold ${RISK_COLORS[workspace.overall_risk] || 'text-zinc-400'}`}>
            {workspace.overall_risk.toUpperCase()}
          </div>
        </div>
      </div>

      {workspace.repos.map((repo) => (
        <div key={repo.path} className="border border-zinc-700 rounded p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-zinc-200">{repo.name}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${HEALTH_COLORS[repo.health] || 'text-zinc-500'}`}>
              {repo.health}
            </span>
          </div>
          <div className="text-xs text-zinc-500 space-y-0.5">
            <div>Branch: <span className="text-zinc-300">{repo.branch}</span></div>
            <div>Dirty: {repo.dirty} | Staged: {repo.staged} | Branches: {repo.branches} | WTs: {repo.worktrees}</div>
            {repo.issues.length > 0 && (
              <div className="text-amber-400 mt-1">{repo.issues.join(' · ')}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function RepositoriesTab() {
  const { repositories, fetchRepositories, loading } = useMetaIDEStore()

  useEffect(() => { fetchRepositories() }, [])

  if (loading && repositories.length === 0) return <div className="p-4 text-zinc-500">Loading...</div>
  if (repositories.length === 0) return <div className="p-4 text-zinc-500">No repositories found</div>

  return (
    <div className="p-4 space-y-4">
      {repositories.map((repo) => (
        <div key={repo.repo_path} className="border border-zinc-700 rounded p-3 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-zinc-200">{repo.repo_name}</span>
            <span className={`text-xs ${HEALTH_COLORS[repo.health.status]}`}>{repo.health.status}</span>
          </div>

          <div className="text-xs text-zinc-400">
            <span className="text-zinc-300">{repo.current_branch}</span> @ {repo.head_commit.slice(0, 8)}
          </div>

          {repo.dirty_files.length > 0 && (
            <div className="text-xs">
              <div className="text-amber-400 mb-1">Dirty ({repo.dirty_files.length})</div>
              <div className="max-h-24 overflow-y-auto space-y-0.5">
                {repo.dirty_files.slice(0, 10).map((f) => (
                  <div key={f} className="text-zinc-500 font-mono truncate">{f}</div>
                ))}
                {repo.dirty_files.length > 10 && <div className="text-zinc-600">...and {repo.dirty_files.length - 10} more</div>}
              </div>
            </div>
          )}

          {repo.worktrees.length > 1 && (
            <div className="text-xs">
              <div className="text-cyan-400 mb-1">Worktrees ({repo.worktrees.length})</div>
              {repo.worktrees.map((w) => (
                <div key={w.path} className="flex items-center gap-2 text-zinc-500">
                  <span className="font-mono truncate flex-1">{w.branch || '(detached)'}</span>
                  {w.locked && <span className="text-amber-400 text-[10px]">LOCKED</span>}
                  {w.detached && <span className="text-red-400 text-[10px]">DETACHED</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function RoadmapTab() {
  const { roadmap, fetchRoadmap, loading } = useMetaIDEStore()

  useEffect(() => { fetchRoadmap() }, [])

  if (loading && !roadmap) return <div className="p-4 text-zinc-500">Loading roadmap...</div>
  if (!roadmap) return <div className="p-4 text-zinc-500">No roadmap data</div>

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Total Phases" value={roadmap.total_phases} />
        <StatCard label="Completed" value={roadmap.completed_phases.length} />
      </div>

      <div className="border border-zinc-700 rounded p-3">
        <div className="text-xs text-zinc-500 mb-1">Progress</div>
        <div className="h-2 bg-zinc-800 rounded overflow-hidden">
          <div
            className="h-full bg-green-500 rounded"
            style={{ width: `${Math.round(roadmap.completion_ratio * 100)}%` }}
          />
        </div>
        <div className="text-xs text-zinc-400 mt-1">{Math.round(roadmap.completion_ratio * 100)}% complete</div>
      </div>

      {roadmap.current_phase && (
        <div className="border border-cyan-800 rounded p-3">
          <div className="text-xs text-cyan-400 mb-1">Current Phase</div>
          <div className="text-sm text-zinc-200">
            Phase {roadmap.current_phase.phase_number}: {roadmap.current_phase.phase_name}
          </div>
        </div>
      )}

      {roadmap.completed_phases.length > 0 && (
        <div>
          <div className="text-xs text-zinc-500 mb-2">Completed ({roadmap.completed_phases.length})</div>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {roadmap.completed_phases.map((p) => (
              <PhaseRow key={p.phase_number} phase={p} />
            ))}
          </div>
        </div>
      )}

      {roadmap.planned_phases.length > 0 && (
        <div>
          <div className="text-xs text-zinc-500 mb-2">Planned ({roadmap.planned_phases.length})</div>
          <div className="space-y-1">
            {roadmap.planned_phases.map((p) => (
              <PhaseRow key={p.phase_number} phase={p} />
            ))}
          </div>
        </div>
      )}

      {roadmap.blocked_phases.length > 0 && (
        <div>
          <div className="text-xs text-red-400 mb-2">Blocked ({roadmap.blocked_phases.length})</div>
          <div className="space-y-1">
            {roadmap.blocked_phases.map((p) => (
              <PhaseRow key={p.phase_number} phase={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function RisksTab() {
  const { risks, overallRisk, fetchRisks, loading } = useMetaIDEStore()

  useEffect(() => { fetchRisks() }, [])

  if (loading && risks.length === 0) return <div className="p-4 text-zinc-500">Loading risks...</div>

  return (
    <div className="p-4 space-y-4">
      <div className="border border-zinc-700 rounded p-3 flex items-center justify-between">
        <span className="text-xs text-zinc-500">Overall Risk</span>
        <span className={`text-sm font-bold ${RISK_COLORS[overallRisk] || 'text-zinc-400'}`}>
          {overallRisk.toUpperCase()}
        </span>
      </div>

      {risks.length === 0 ? (
        <div className="text-zinc-500 text-sm">No engineering risks detected.</div>
      ) : (
        <div className="space-y-2">
          {risks.map((r) => (
            <div key={r.id} className="border border-zinc-700 rounded p-3">
              <div className="flex items-center justify-between mb-1">
                <span className={`text-xs font-medium ${RISK_COLORS[r.level]}`}>{r.level.toUpperCase()}</span>
                <span className="text-xs text-zinc-600">{r.category}</span>
              </div>
              <div className="text-sm text-zinc-300">{r.description}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TerminalsTab() {
  const { observation, fetchObservation, loading } = useMetaIDEStore()

  useEffect(() => { fetchObservation() }, [])

  const terminals = observation?.terminals || []
  if (loading && terminals.length === 0) return <div className="p-4 text-zinc-500">Loading terminals...</div>
  if (terminals.length === 0) return <div className="p-4 text-zinc-500">No active terminals</div>

  return (
    <div className="p-4 space-y-2">
      {terminals.map((t) => (
        <div key={t.terminal_id} className="border border-zinc-700 rounded p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-zinc-200">{t.session_name}</span>
            <span className={`text-xs ${t.is_active ? 'text-green-400' : 'text-zinc-600'}`}>
              {t.is_active ? '● active' : '○ idle'}
            </span>
          </div>
          <div className="text-xs text-zinc-500 space-y-0.5">
            <div>Window: <span className="text-zinc-300">{t.window_name || '—'}</span> Pane: {t.pane_index}</div>
            {t.current_command && <div>Command: <span className="text-cyan-400 font-mono">{t.current_command}</span></div>}
            {t.cwd && <div className="text-zinc-600 font-mono truncate">{t.cwd}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

function ContainersTab() {
  const { observation, fetchObservation, loading } = useMetaIDEStore()

  useEffect(() => { fetchObservation() }, [])

  const containers = observation?.containers || []
  if (loading && containers.length === 0) return <div className="p-4 text-zinc-500">Loading containers...</div>
  if (containers.length === 0) return <div className="p-4 text-zinc-500">No containers found</div>

  return (
    <div className="p-4 space-y-2">
      {containers.map((c) => (
        <div key={c.container_id} className="border border-zinc-700 rounded p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-zinc-200">{c.container_name}</span>
            <span className={`text-xs ${HEALTH_COLORS[c.health] || 'text-zinc-500'}`}>
              ● {c.health}
            </span>
          </div>
          <div className="text-xs text-zinc-500 space-y-0.5">
            <div>Image: <span className="text-zinc-400 font-mono">{c.image}</span></div>
            <div>Status: <span className="text-zinc-300">{c.status}</span></div>
            {c.ports.length > 0 && <div>Ports: <span className="text-cyan-400">{c.ports.join(', ')}</span></div>}
            {c.restart_count > 0 && <div className="text-amber-400">Restarts: {c.restart_count}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

function PreviewsTab() {
  const { observation, fetchObservation, loading } = useMetaIDEStore()

  useEffect(() => { fetchObservation() }, [])

  const previews = observation?.previews || []
  if (loading && previews.length === 0) return <div className="p-4 text-zinc-500">Loading previews...</div>
  if (previews.length === 0) return <div className="p-4 text-zinc-500">No dev servers detected</div>

  return (
    <div className="p-4 space-y-2">
      {previews.map((p) => (
        <div key={p.preview_id} className="border border-zinc-700 rounded p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-zinc-200">{p.name}</span>
            <span className={`text-xs ${HEALTH_COLORS[p.health] || 'text-zinc-500'}`}>
              ● {p.health}
            </span>
          </div>
          <div className="text-xs text-zinc-500 space-y-0.5">
            <div>URL: <span className="text-cyan-400 font-mono">{p.url}</span></div>
            <div>Port: {p.port} | Process: <span className="text-zinc-300">{p.process_name || '—'}</span></div>
            {p.restart_count > 0 && <div className="text-amber-400">Restarts: {p.restart_count}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

function StatCard({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className="border border-zinc-700 rounded p-3">
      <div className="text-xs text-zinc-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${warn ? 'text-amber-400' : 'text-zinc-200'}`}>{value}</div>
    </div>
  )
}

function PhaseRow({ phase }: { phase: { phase_number: string; phase_name: string; state: string } }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={`${STATE_COLORS[phase.state] || 'text-zinc-500'}`}>●</span>
      <span className="text-zinc-400 w-8">P{phase.phase_number}</span>
      <span className="text-zinc-300 truncate flex-1">{phase.phase_name}</span>
    </div>
  )
}

function ContextSidebar() {
  const [ctx, setCtx] = useState<Record<string, unknown> | null>(null)
  const [collapsed, setCollapsed] = useState(false)

  usePolling(useCallback(() => {
    fetchApi('/meta-ide-context/context').then(setCtx).catch(() => {})
  }, []), 10000, true, 1000)

  if (collapsed) {
    return (
      <div className="w-8 border-r border-zinc-800 flex flex-col items-center pt-2 shrink-0">
        <button onClick={() => setCollapsed(false)} className="p-1 text-zinc-500 hover:text-zinc-300">
          <ChevronRight size={14} />
        </button>
      </div>
    )
  }

  const project = (ctx?.active_project as string) || ''
  const repo = (ctx?.active_repo as string) || ''
  const goals = (ctx?.related_goals as Array<Record<string, string>>) || []
  const decisions = (ctx?.related_decisions as Array<Record<string, string>>) || []
  const constraints = (ctx?.constraints as string[]) || []

  return (
    <div className="w-[240px] border-r border-zinc-800 overflow-y-auto p-3 shrink-0">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-zinc-400 uppercase tracking-wider">Context</span>
        <button onClick={() => setCollapsed(true)} className="p-0.5 text-zinc-500 hover:text-zinc-300">
          <ChevronLeft size={12} />
        </button>
      </div>

      {project && <div className="text-[11px] mb-1"><span className="text-zinc-500">Project</span> <span className="text-zinc-200">{project}</span></div>}
      {repo && <div className="text-[11px] mb-3"><span className="text-zinc-500">Repo</span> <span className="text-zinc-200">{repo}</span></div>}

      {goals.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Goals</div>
          {goals.slice(0, 5).map((g, i) => (
            <div key={i} className="text-[11px] text-zinc-300 py-0.5">{g.title || g.description || ''}</div>
          ))}
        </div>
      )}

      {decisions.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Decisions</div>
          {decisions.slice(0, 5).map((d, i) => (
            <div key={i} className="text-[11px] text-zinc-300 py-0.5">{d.title || d.description || ''}</div>
          ))}
        </div>
      )}

      {constraints.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Constraints</div>
          {constraints.slice(0, 5).map((c, i) => (
            <div key={i} className="text-[11px] text-amber-400 py-0.5">{c}</div>
          ))}
        </div>
      )}

      {!project && !repo && goals.length === 0 && (
        <div className="text-[11px] text-zinc-600 text-center py-4">No context available</div>
      )}
    </div>
  )
}

export function MetaIDEPanel() {
  const { activeTab, setActiveTab } = useMetaIDEStore()

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex items-center gap-1 px-4 py-2 border-b border-zinc-800">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1.5 text-xs rounded transition-colors ${
              activeTab === tab
                ? 'bg-zinc-700 text-zinc-100'
                : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <ContextSidebar />
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'files' && <FilesTab />}
          {activeTab === 'workspace' && <WorkspaceTab />}
          {activeTab === 'repositories' && <RepositoriesTab />}
          {activeTab === 'roadmap' && <RoadmapTab />}
          {activeTab === 'risks' && <RisksTab />}
          {activeTab === 'terminals' && <TerminalsTab />}
          {activeTab === 'containers' && <ContainersTab />}
          {activeTab === 'previews' && <PreviewsTab />}
        </div>
      </div>
    </div>
  )
}
