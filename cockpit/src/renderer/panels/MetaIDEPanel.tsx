import { useEffect } from 'react'
import { useMetaIDEStore } from '../stores/metaIDEStore'

const TABS = ['workspace', 'repositories', 'roadmap', 'risks'] as const

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
}

const STATE_COLORS: Record<string, string> = {
  completed: 'text-green-400',
  in_progress: 'text-cyan-400',
  planned: 'text-zinc-400',
  blocked: 'text-red-400',
  unknown: 'text-zinc-500',
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

      <div className="flex-1 overflow-y-auto">
        {activeTab === 'workspace' && <WorkspaceTab />}
        {activeTab === 'repositories' && <RepositoriesTab />}
        {activeTab === 'roadmap' && <RoadmapTab />}
        {activeTab === 'risks' && <RisksTab />}
      </div>
    </div>
  )
}
