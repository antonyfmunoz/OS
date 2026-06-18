import { useEffect, useState } from 'react'
import {
  Target,
  RefreshCw,
  AlertTriangle,
  TrendingUp,
  Crosshair,
  Map,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react'
import { useGoalStore } from '../stores/goalStore'

type Tab = 'goals' | 'outcomes' | 'plans' | 'alignment' | 'drift'

const STATUS_COLORS: Record<string, string> = {
  active: 'text-green-400 bg-green-400/10',
  completed: 'text-cyan bg-cyan/10',
  paused: 'text-yellow-400 bg-yellow-400/10',
  abandoned: 'text-text-tertiary bg-surface-raised',
  draft: 'text-text-tertiary bg-surface-raised',
  on_track: 'text-green-400 bg-green-400/10',
  at_risk: 'text-orange-400 bg-orange-400/10',
  blocked: 'text-red-400 bg-red-400/10',
  not_started: 'text-text-tertiary bg-surface-raised',
  healthy: 'text-green-400 bg-green-400/10',
  watch: 'text-yellow-400 bg-yellow-400/10',
  degraded: 'text-orange-400 bg-orange-400/10',
  critical: 'text-red-400 bg-red-400/10',
}

const DRIFT_COLORS: Record<string, string> = {
  activity_drift: 'text-orange-400 bg-orange-400/10',
  alignment_drift: 'text-red-400 bg-red-400/10',
  outcome_drift: 'text-yellow-400 bg-yellow-400/10',
  planning_drift: 'text-cyan bg-cyan/10',
}

function Badge({ text, color }: { text: string; color?: string }) {
  const cls = color ?? STATUS_COLORS[text.toLowerCase()] ?? 'text-text-tertiary bg-surface-raised'
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-mono ${cls}`}>
      {text.toUpperCase().replace(/_/g, ' ')}
    </span>
  )
}

function SectionCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="border border-border rounded-lg p-3 bg-surface-base">
      {children}
    </div>
  )
}

function ProgressBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 75 ? 'bg-green-400' : pct >= 50 ? 'bg-yellow-400' : pct >= 25 ? 'bg-orange-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-surface-raised rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-text-tertiary w-8 text-right">{pct}%</span>
    </div>
  )
}

function GoalsTab() {
  const { goals, tree, hierarchySummary } = useGoalStore()
  const summary = hierarchySummary as Record<string, unknown> | null
  const byType = (summary?.by_type as Record<string, number>) ?? {}

  return (
    <div className="space-y-3">
      <SectionCard>
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-4 h-4 text-cyan" />
          <span className="text-sm font-medium text-text-primary">Hierarchy</span>
          {summary?.valid ? (
            <CheckCircle2 className="w-3 h-3 text-green-400" />
          ) : (
            <XCircle className="w-3 h-3 text-red-400" />
          )}
        </div>
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <span className="text-text-tertiary">Total</span>
            <div className="text-lg font-mono text-text-primary">{summary?.total_goals ?? 0}</div>
          </div>
          <div>
            <span className="text-text-tertiary">Roots</span>
            <div className="text-lg font-mono text-text-primary">{summary?.root_count ?? 0}</div>
          </div>
          <div>
            <span className="text-text-tertiary">Depth</span>
            <div className="text-lg font-mono text-text-primary">{summary?.max_depth ?? 0}</div>
          </div>
        </div>
        {Object.keys(byType).length > 0 && (
          <div className="flex gap-2 mt-2 flex-wrap">
            {Object.entries(byType).map(([type, count]) => (
              <span key={type} className="text-xs text-text-secondary">
                {type}: <span className="font-mono">{count}</span>
              </span>
            ))}
          </div>
        )}
      </SectionCard>

      {goals.map((goal) => {
        const g = goal as Record<string, unknown>
        return (
          <SectionCard key={g.goal_id as string}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-text-primary font-medium truncate">{g.title as string}</span>
              <Badge text={g.status as string} />
            </div>
            <div className="flex items-center gap-2 text-xs text-text-tertiary">
              <Badge text={g.goal_type as string} />
              {g.domain ? <span>{g.domain as string}</span> : null}
              {g.priority ? <span>P{g.priority as number}</span> : null}
            </div>
            {g.description ? (
              <p className="text-xs text-text-secondary mt-1 line-clamp-2">{g.description as string}</p>
            ) : null}
          </SectionCard>
        )
      })}

      {goals.length === 0 && (
        <p className="text-xs text-text-tertiary text-center py-4">No active goals</p>
      )}
    </div>
  )
}

function OutcomesTab() {
  const { outcomes } = useGoalStore()
  const snap = outcomes as Record<string, unknown> | null
  const goalList = (snap?.goals as Record<string, unknown>[]) ?? []

  return (
    <div className="space-y-3">
      <SectionCard>
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="w-4 h-4 text-cyan" />
          <span className="text-sm font-medium text-text-primary">Overall</span>
          <Badge text={snap?.overall_health as string ?? 'unknown'} />
        </div>
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <span className="text-text-tertiary">Active</span>
            <div className="text-lg font-mono text-text-primary">{snap?.total_active ?? 0}</div>
          </div>
          <div>
            <span className="text-text-tertiary">Done</span>
            <div className="text-lg font-mono text-text-primary">{snap?.total_completed ?? 0}</div>
          </div>
          <div>
            <span className="text-text-tertiary">Blocked</span>
            <div className="text-lg font-mono text-text-primary">{snap?.total_blocked ?? 0}</div>
          </div>
        </div>
      </SectionCard>

      {goalList.map((g) => (
        <SectionCard key={g.goal_id as string}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-text-primary truncate">{g.title as string}</span>
            <Badge text={g.health as string} />
          </div>
          <ProgressBar value={g.percent_complete as number ?? 0} />
          <div className="flex gap-3 mt-1 text-xs text-text-tertiary">
            <span>{g.criteria_met as number}/{g.criteria_total as number} criteria</span>
            <span>{g.active_work_count as number} active</span>
            {(g.blocker_count as number) > 0 && (
              <span className="text-red-400">{g.blocker_count as number} blocked</span>
            )}
          </div>
        </SectionCard>
      ))}
    </div>
  )
}

function PlansTab() {
  const { plans } = useGoalStore()
  const roadmap = plans as Record<string, unknown> | null
  const planList = (roadmap?.plans as Record<string, unknown>[]) ?? []

  return (
    <div className="space-y-3">
      <SectionCard>
        <div className="flex items-center gap-2 mb-2">
          <Map className="w-4 h-4 text-cyan" />
          <span className="text-sm font-medium text-text-primary">Roadmap</span>
        </div>
        <div className="grid grid-cols-4 gap-2 text-xs">
          <div>
            <span className="text-text-tertiary">Total</span>
            <div className="text-lg font-mono text-text-primary">{roadmap?.total ?? 0}</div>
          </div>
          <div>
            <span className="text-green-400">On Track</span>
            <div className="text-lg font-mono text-text-primary">{roadmap?.on_track ?? 0}</div>
          </div>
          <div>
            <span className="text-orange-400">At Risk</span>
            <div className="text-lg font-mono text-text-primary">{roadmap?.at_risk ?? 0}</div>
          </div>
          <div>
            <span className="text-red-400">Blocked</span>
            <div className="text-lg font-mono text-text-primary">{roadmap?.blocked ?? 0}</div>
          </div>
        </div>
      </SectionCard>

      {planList.map((p) => (
        <SectionCard key={p.goal_id as string}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-text-primary truncate">{p.goal_title as string}</span>
            <Badge text={p.status as string} />
          </div>
          <Badge text={p.goal_type as string} />
          {((p.blockers as string[]) ?? []).length > 0 && (
            <div className="mt-2">
              <span className="text-xs text-red-400">Blockers:</span>
              {((p.blockers as string[]) ?? []).map((b, i) => (
                <p key={i} className="text-xs text-text-secondary ml-2">- {b}</p>
              ))}
            </div>
          )}
          {((p.milestones as Record<string, unknown>[]) ?? []).length > 0 && (
            <div className="mt-2">
              <span className="text-xs text-text-tertiary">Milestones:</span>
              {((p.milestones as Record<string, unknown>[]) ?? []).map((m, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-text-secondary ml-2">
                  <Badge text={m.status as string} />
                  <span>{m.title as string}</span>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      ))}
    </div>
  )
}

function AlignmentTab() {
  const { alignment } = useGoalStore()
  const report = alignment as Record<string, unknown> | null
  const score = (report?.alignment_score as number) ?? 0
  const unlinked = (report?.unlinked_items as Record<string, unknown>[]) ?? []
  const orphans = (report?.orphan_goals as Record<string, unknown>[]) ?? []

  return (
    <div className="space-y-3">
      <SectionCard>
        <div className="flex items-center gap-2 mb-2">
          <Crosshair className="w-4 h-4 text-cyan" />
          <span className="text-sm font-medium text-text-primary">Alignment Score</span>
        </div>
        <div className="text-3xl font-mono text-text-primary mb-1">{Math.round(score * 100)}%</div>
        <ProgressBar value={score} />
        <div className="grid grid-cols-3 gap-2 mt-2 text-xs">
          <div>
            <span className="text-text-tertiary">Total Work</span>
            <div className="font-mono text-text-primary">{report?.total_work_count ?? 0}</div>
          </div>
          <div>
            <span className="text-green-400">Linked</span>
            <div className="font-mono text-text-primary">{report?.linked_work_count ?? 0}</div>
          </div>
          <div>
            <span className="text-red-400">Unlinked</span>
            <div className="font-mono text-text-primary">{report?.unlinked_work_count ?? 0}</div>
          </div>
        </div>
      </SectionCard>

      {orphans.length > 0 && (
        <SectionCard>
          <div className="text-xs text-orange-400 mb-1">Orphan Goals (no active work)</div>
          {orphans.map((o, i) => (
            <div key={i} className="text-xs text-text-secondary">- {o.title as string}</div>
          ))}
        </SectionCard>
      )}

      {unlinked.length > 0 && (
        <SectionCard>
          <div className="text-xs text-red-400 mb-1">Unlinked Work</div>
          {unlinked.slice(0, 10).map((u, i) => (
            <div key={i} className="text-xs text-text-secondary truncate">- {u.title as string || u.work_id as string}</div>
          ))}
          {unlinked.length > 10 && (
            <div className="text-xs text-text-tertiary mt-1">+{unlinked.length - 10} more</div>
          )}
        </SectionCard>
      )}
    </div>
  )
}

function DriftTab() {
  const { drift } = useGoalStore()
  const snap = drift as Record<string, unknown> | null
  const warnings = (snap?.warnings as Record<string, unknown>[]) ?? []
  const byType = (snap?.drift_by_type as Record<string, number>) ?? {}

  return (
    <div className="space-y-3">
      <SectionCard>
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-4 h-4 text-cyan" />
          <span className="text-sm font-medium text-text-primary">Goal Drift</span>
          <Badge text={snap?.overall_drift_health as string ?? 'unknown'} />
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-text-tertiary">Warnings</span>
            <div className="text-lg font-mono text-text-primary">{snap?.warning_count ?? 0}</div>
          </div>
          <div>
            <span className="text-red-400">High Priority</span>
            <div className="text-lg font-mono text-text-primary">{snap?.high_drift_count ?? 0}</div>
          </div>
        </div>
        {Object.keys(byType).length > 0 && (
          <div className="flex gap-2 mt-2 flex-wrap">
            {Object.entries(byType).map(([type, count]) => (
              <span key={type} className="text-xs">
                <Badge text={type} color={DRIFT_COLORS[type]} /> <span className="font-mono text-text-tertiary">{count}</span>
              </span>
            ))}
          </div>
        )}
      </SectionCard>

      {warnings.map((w, i) => (
        <SectionCard key={i}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-text-primary truncate">{w.goal_title as string}</span>
            <Badge text={w.severity as string} />
          </div>
          <Badge text={w.drift_type as string} color={DRIFT_COLORS[w.drift_type as string]} />
          <p className="text-xs text-text-secondary mt-1">{w.description as string}</p>
          {((w.evidence as string[]) ?? []).length > 0 && (
            <div className="text-xs text-text-tertiary mt-1 font-mono">
              {((w.evidence as string[]) ?? []).map((e, j) => (
                <div key={j}>{e}</div>
              ))}
            </div>
          )}
        </SectionCard>
      ))}

      {warnings.length === 0 && (
        <p className="text-xs text-text-tertiary text-center py-4">No drift detected</p>
      )}
    </div>
  )
}

const TABS: { id: Tab; label: string; icon: typeof Target }[] = [
  { id: 'goals', label: 'Goals', icon: Target },
  { id: 'outcomes', label: 'Outcomes', icon: TrendingUp },
  { id: 'plans', label: 'Plans', icon: Map },
  { id: 'alignment', label: 'Alignment', icon: Crosshair },
  { id: 'drift', label: 'Drift', icon: AlertTriangle },
]

export function GoalPanel() {
  const [tab, setTab] = useState<Tab>('goals')
  const {
    fetchGoals,
    fetchTree,
    fetchPlans,
    fetchAlignment,
    fetchOutcomes,
    fetchDrift,
    fetchHierarchySummary,
    loading,
  } = useGoalStore()

  useEffect(() => {
    fetchGoals()
    fetchTree()
    fetchHierarchySummary()
    fetchOutcomes()
    fetchPlans()
    fetchAlignment()
    fetchDrift()
  }, [])

  const refresh = () => {
    fetchGoals()
    fetchTree()
    fetchHierarchySummary()
    fetchOutcomes()
    fetchPlans()
    fetchAlignment()
    fetchDrift()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-cyan" />
          <span className="text-sm font-medium text-text-primary">Goals & Strategy</span>
        </div>
        <button
          onClick={refresh}
          className="p-1 rounded hover:bg-surface-raised text-text-tertiary"
          title="Refresh"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="flex border-b border-border">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs transition-colors ${
              tab === id
                ? 'text-cyan border-b-2 border-cyan'
                : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            <Icon className="w-3 h-3" />
            {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {tab === 'goals' && <GoalsTab />}
        {tab === 'outcomes' && <OutcomesTab />}
        {tab === 'plans' && <PlansTab />}
        {tab === 'alignment' && <AlignmentTab />}
        {tab === 'drift' && <DriftTab />}
      </div>
    </div>
  )
}
