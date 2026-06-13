import { useState, useEffect, useCallback } from 'react'
import { useOperatorLoopStore } from '../stores/operatorLoopStore'

type ContinuityTab = 'overview' | 'objectives' | 'loops' | 'approvals' | 'timeline'

export function ContinuityPanel() {
  const [tab, setTab] = useState<ContinuityTab>('overview')
  const {
    continuityStatus,
    continuitySnapshot,
    continuityBrief,
    continuityTimeline,
    continuityResume,
    continuityLoading,
    fetchContinuityStatus,
    fetchContinuitySnapshot,
    fetchContinuityBrief,
    fetchContinuityTimeline,
    captureContinuitySnapshot,
    generateContinuityBrief,
    recordContinuityDeparture,
    generateContinuityResume,
    recordContinuityInteraction,
  } = useOperatorLoopStore()

  useEffect(() => {
    fetchContinuityStatus()
    fetchContinuitySnapshot()
    fetchContinuityBrief()
    fetchContinuityTimeline()
  }, [])

  const tabs: { id: ContinuityTab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'objectives', label: 'Objectives' },
    { id: 'loops', label: 'Loops' },
    { id: 'approvals', label: 'Approvals' },
    { id: 'timeline', label: 'Timeline' },
  ]

  return (
    <div className="h-full overflow-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Continuity</h2>
        <div className="flex gap-2">
          <button
            onClick={() => { captureContinuitySnapshot(); recordContinuityInteraction() }}
            disabled={continuityLoading}
            className="px-3 py-1 text-xs rounded bg-cyan-600 hover:bg-cyan-700 text-white disabled:opacity-50"
          >
            Capture
          </button>
          <button
            onClick={() => generateContinuityBrief()}
            disabled={continuityLoading}
            className="px-3 py-1 text-xs rounded bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-50"
          >
            Brief
          </button>
          <button
            onClick={() => generateContinuityResume()}
            disabled={continuityLoading}
            className="px-3 py-1 text-xs rounded bg-amber-600 hover:bg-amber-700 text-white disabled:opacity-50"
          >
            Resume
          </button>
        </div>
      </div>

      <div className="flex gap-1 border-b border-border">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 text-xs font-medium border-b-2 transition-colors ${
              tab === t.id
                ? 'border-cyan-500 text-cyan-400'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab />}
      {tab === 'objectives' && <ObjectivesTab />}
      {tab === 'loops' && <LoopsTab />}
      {tab === 'approvals' && <ApprovalsTab />}
      {tab === 'timeline' && <TimelineTab />}
    </div>
  )
}

function OverviewTab() {
  const { continuityStatus, continuitySnapshot, continuityBrief, continuityResume } = useOperatorLoopStore()

  return (
    <div className="space-y-4">
      {/* Status KPIs */}
      <div className="grid grid-cols-4 gap-3">
        <KpiCard label="State" value={continuityStatus?.state ?? 'idle'} />
        <KpiCard label="Attention" value={continuityStatus?.attention?.state ?? 'offline'} />
        <KpiCard label="Snapshots" value={String(continuityStatus?.run_count ?? 0)} />
        <KpiCard label="Handoffs" value={String(continuityStatus?.handoff_count ?? 0)} />
      </div>

      {/* Brief Section */}
      {continuityBrief && (
        <div className="bg-surface-raised rounded-lg border border-border p-4 space-y-3">
          <h3 className="text-sm font-semibold text-text-primary">Executive Brief</h3>
          <div className="text-sm text-text-secondary">{continuityBrief.mission_status}</div>
          <div className="text-xs text-text-tertiary">{continuityBrief.current_reality}</div>

          <div className="grid grid-cols-3 gap-3 mt-2">
            <MiniKpi label="Objectives" value={continuityBrief.active_objectives_count} />
            <MiniKpi label="Active Work" value={continuityBrief.active_work_count} />
            <MiniKpi label="Blocked" value={continuityBrief.blocked_count} color="red" />
            <MiniKpi label="Approvals" value={continuityBrief.approval_count} color="amber" />
            <MiniKpi label="Risks" value={continuityBrief.risk_count} color="red" />
            <MiniKpi label="Opportunities" value={continuityBrief.opportunity_count} color="green" />
          </div>

          {continuityBrief.critical_changes?.length > 0 && (
            <div className="mt-2">
              <div className="text-xs font-medium text-red-400 mb-1">Critical Changes</div>
              {continuityBrief.critical_changes.map((c: string, i: number) => (
                <div key={i} className="text-xs text-text-secondary">• {c}</div>
              ))}
            </div>
          )}

          {continuityBrief.recommended_actions?.length > 0 && (
            <div className="mt-2">
              <div className="text-xs font-medium text-cyan-400 mb-1">Recommended Actions</div>
              {continuityBrief.recommended_actions.map((a: string, i: number) => (
                <div key={i} className="text-xs text-text-secondary">→ {a}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Resume Report */}
      {continuityResume && (
        <div className="bg-surface-raised rounded-lg border border-border p-4 space-y-3">
          <h3 className="text-sm font-semibold text-text-primary">Resume Report</h3>
          <div className="text-xs text-text-tertiary">
            Absence: {formatDuration(continuityResume.absence_duration_seconds)}
          </div>

          {continuityResume.completed?.length > 0 && (
            <ChangeList title="Completed" items={continuityResume.completed} color="green" />
          )}
          {continuityResume.failed?.length > 0 && (
            <ChangeList title="Failed" items={continuityResume.failed} color="red" />
          )}
          {continuityResume.blocked?.length > 0 && (
            <ChangeList title="Blocked" items={continuityResume.blocked} color="amber" />
          )}
          {continuityResume.became_available?.length > 0 && (
            <ChangeList title="Became Available" items={continuityResume.became_available} color="cyan" />
          )}
          {continuityResume.needs_review?.length > 0 && (
            <ChangeList title="Needs Review" items={continuityResume.needs_review} color="purple" />
          )}
        </div>
      )}

      {/* Current Snapshot Summary */}
      {continuitySnapshot && (
        <div className="bg-surface-raised rounded-lg border border-border p-4 space-y-2">
          <h3 className="text-sm font-semibold text-text-primary">Current Snapshot</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="text-text-tertiary">Profile: <span className="text-text-secondary">{continuitySnapshot.active_profile_mode || 'none'}</span></div>
            <div className="text-text-tertiary">Attention: <span className="text-text-secondary">{continuitySnapshot.operator_attention}</span></div>
            <div className="text-text-tertiary">Objectives: <span className="text-text-secondary">{continuitySnapshot.active_objectives?.length ?? 0}</span></div>
            <div className="text-text-tertiary">Work Packets: <span className="text-text-secondary">{continuitySnapshot.active_work_packets?.length ?? 0}</span></div>
            <div className="text-text-tertiary">Blocked: <span className="text-text-secondary">{continuitySnapshot.blocked_items?.length ?? 0}</span></div>
            <div className="text-text-tertiary">Approvals: <span className="text-text-secondary">{continuitySnapshot.approvals_waiting?.length ?? 0}</span></div>
            <div className="text-text-tertiary">Risks: <span className="text-text-secondary">{continuitySnapshot.active_risks?.length ?? 0}</span></div>
            <div className="text-text-tertiary">Opportunities: <span className="text-text-secondary">{continuitySnapshot.active_opportunities?.length ?? 0}</span></div>
          </div>
        </div>
      )}
    </div>
  )
}

function ObjectivesTab() {
  const { continuitySnapshot } = useOperatorLoopStore()
  const objectives = continuitySnapshot?.active_objectives ?? []

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-text-primary">Active Objectives ({objectives.length})</h3>
      {objectives.length === 0 && (
        <div className="text-xs text-text-tertiary">No active objectives</div>
      )}
      {objectives.map((obj: any, i: number) => (
        <div key={i} className="bg-surface-raised rounded-lg border border-border p-3">
          <div className="flex items-center justify-between mb-1">
            <div className="text-sm font-medium text-text-primary">{obj.title}</div>
            <span className="text-xs px-2 py-0.5 rounded bg-cyan-900/30 text-cyan-400">{obj.domain}</span>
          </div>
          <div className="flex gap-4 text-xs text-text-tertiary">
            <span>Status: {obj.status}</span>
            <span>Progress: {Math.round((obj.progress ?? 0) * 100)}%</span>
            <span>Priority: {obj.priority}</span>
          </div>
          {obj.progress != null && (
            <div className="mt-2 h-1.5 bg-surface rounded-full overflow-hidden">
              <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${Math.min(100, (obj.progress ?? 0) * 100)}%` }} />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function LoopsTab() {
  const { continuitySnapshot } = useOperatorLoopStore()
  const loops = continuitySnapshot?.active_loops ?? []

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-text-primary">Active Loops ({loops.length})</h3>
      {loops.length === 0 && (
        <div className="text-xs text-text-tertiary">No active loops</div>
      )}
      {loops.map((loop: any, i: number) => (
        <div key={i} className="bg-surface-raised rounded-lg border border-border p-3">
          <div className="flex items-center justify-between mb-1">
            <div className="text-sm font-medium text-text-primary">{loop.type}</div>
            <span className={`text-xs px-2 py-0.5 rounded ${
              loop.state === 'running' ? 'bg-emerald-900/30 text-emerald-400' : 'bg-zinc-800 text-text-tertiary'
            }`}>{loop.state}</span>
          </div>
          <div className="flex gap-4 text-xs text-text-tertiary">
            <span>Frequency: {loop.frequency}</span>
            <span>Ticks: {loop.tick_count}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

function ApprovalsTab() {
  const { continuitySnapshot } = useOperatorLoopStore()
  const approvals = continuitySnapshot?.approvals_waiting ?? []

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-text-primary">Pending Approvals ({approvals.length})</h3>
      {approvals.length === 0 && (
        <div className="text-xs text-text-tertiary">No pending approvals</div>
      )}
      {approvals.map((a: any, i: number) => (
        <div key={i} className="bg-surface-raised rounded-lg border border-border p-3">
          <div className="flex items-center justify-between mb-1">
            <div className="text-sm font-medium text-text-primary">{a.title}</div>
            <span className={`text-xs px-2 py-0.5 rounded ${
              a.risk_level === 'high' || a.risk_level === 'critical'
                ? 'bg-red-900/30 text-red-400'
                : 'bg-amber-900/30 text-amber-400'
            }`}>{a.risk_level}</span>
          </div>
          <div className="text-xs text-text-tertiary">{a.description}</div>
          <div className="text-xs text-text-tertiary mt-1">Agent: {a.agent}</div>
        </div>
      ))}
    </div>
  )
}

function TimelineTab() {
  const { continuityTimeline, fetchContinuityTimeline } = useOperatorLoopStore()

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">Timeline</h3>
        <button
          onClick={() => fetchContinuityTimeline()}
          className="text-xs text-cyan-400 hover:text-cyan-300"
        >
          Refresh
        </button>
      </div>
      {(!continuityTimeline || continuityTimeline.length === 0) && (
        <div className="text-xs text-text-tertiary">No timeline events</div>
      )}
      {continuityTimeline?.map((event: any, i: number) => (
        <div key={i} className="bg-surface-raised rounded-lg border border-border p-3">
          <div className="flex items-center justify-between mb-1">
            <span className={`text-xs px-2 py-0.5 rounded ${getEventColor(event.event_type)}`}>
              {event.event_type}
            </span>
            <span className="text-xs text-text-tertiary">{formatTimestamp(event.timestamp)}</span>
          </div>
          <div className="text-sm text-text-secondary">{event.summary}</div>
        </div>
      ))}
    </div>
  )
}


// ── Helpers ──────────────────────────────────────────────────────────


function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface-raised rounded-lg border border-border p-3 text-center">
      <div className="text-lg font-semibold text-text-primary">{value}</div>
      <div className="text-xs text-text-tertiary">{label}</div>
    </div>
  )
}

function MiniKpi({ label, value, color }: { label: string; value: number; color?: string }) {
  const textColor = color === 'red' ? 'text-red-400'
    : color === 'amber' ? 'text-amber-400'
    : color === 'green' ? 'text-emerald-400'
    : 'text-text-primary'
  return (
    <div className="text-center">
      <div className={`text-sm font-semibold ${textColor}`}>{value}</div>
      <div className="text-xs text-text-tertiary">{label}</div>
    </div>
  )
}

function ChangeList({ title, items, color }: { title: string; items: any[]; color: string }) {
  const titleColor = color === 'red' ? 'text-red-400'
    : color === 'amber' ? 'text-amber-400'
    : color === 'green' ? 'text-emerald-400'
    : color === 'cyan' ? 'text-cyan-400'
    : 'text-purple-400'
  return (
    <div>
      <div className={`text-xs font-medium ${titleColor} mb-1`}>{title} ({items.length})</div>
      {items.map((item: any, i: number) => (
        <div key={i} className="text-xs text-text-secondary ml-2">• {item.title || item.id}</div>
      ))}
    </div>
  )
}

function getEventColor(type: string): string {
  switch (type) {
    case 'decision': return 'bg-cyan-900/30 text-cyan-400'
    case 'outcome': return 'bg-emerald-900/30 text-emerald-400'
    case 'execution': return 'bg-blue-900/30 text-blue-400'
    case 'approval': return 'bg-amber-900/30 text-amber-400'
    case 'session_start': return 'bg-green-900/30 text-green-400'
    case 'session_end': return 'bg-red-900/30 text-red-400'
    case 'risk_detected': return 'bg-red-900/30 text-red-400'
    default: return 'bg-zinc-800 text-text-tertiary'
  }
}

function formatTimestamp(ts: number): string {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`
  return `${Math.round(seconds / 86400)}d`
}
