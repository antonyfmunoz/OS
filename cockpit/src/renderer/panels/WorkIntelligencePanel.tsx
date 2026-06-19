import { useEffect, useState, useCallback } from 'react'
import {
  Zap,
  CheckCircle2,
  XCircle,
  Clock,
  Users,
  AlertTriangle,
  RefreshCw,
  TrendingUp,
} from 'lucide-react'
import { useWorkIntelligenceStore } from '../stores/workIntelligenceStore'

type Tab = 'overview' | 'ready' | 'blocked' | 'delegation' | 'drift'

const STATUS_COLORS: Record<string, string> = {
  ready: 'text-green-400 bg-green-400/10',
  waiting_approval: 'text-yellow-400 bg-yellow-400/10',
  waiting_capability: 'text-orange-400 bg-orange-400/10',
  waiting_dependency: 'text-blue-400 bg-blue-400/10',
  waiting_delegation: 'text-purple-400 bg-purple-400/10',
  blocked: 'text-red-400 bg-red-400/10',
}

const HEALTH_COLORS: Record<string, string> = {
  thriving: 'text-green-400',
  healthy: 'text-cyan',
  constrained: 'text-yellow-400',
  stalled: 'text-red-400',
  ready: 'text-green-400',
  mostly_ready: 'text-cyan',
  blocked: 'text-red-400',
  unknown: 'text-muted',
}

function Badge({ label, colorClass }: { label: string; colorClass?: string }) {
  const cls = colorClass || STATUS_COLORS[label] || 'text-muted bg-muted/10'
  return (
    <span className={`px-1.5 py-0.5 text-[9px] font-mono uppercase rounded ${cls}`}>
      {label.replace(/_/g, ' ')}
    </span>
  )
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-border rounded-lg p-3 bg-surface-base">
      <div className="text-[10px] font-mono text-muted uppercase tracking-wider mb-2">{title}</div>
      {children}
    </div>
  )
}

function Metric({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-mono text-muted uppercase">{label}</span>
      <span className="text-sm font-mono text-primary">{value}</span>
      {sub && <span className="text-[9px] font-mono text-muted">{sub}</span>}
    </div>
  )
}

export function WorkIntelligencePanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const {
    overview, readyWork, blockedWork, delegation, drift,
    velocity, health, loading, fetchAll,
  } = useWorkIntelligenceStore()

  useEffect(() => { fetchAll() }, [])

  const handleRefresh = useCallback(() => { fetchAll() }, [fetchAll])

  const portfolio = (overview as Record<string, unknown>)?.portfolio as Record<string, unknown> | undefined

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Work Intelligence</span>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-0 border-b border-border px-4 shrink-0">
        {(['overview', 'ready', 'blocked', 'delegation', 'drift'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider border-b-2 ${
              tab === t
                ? 'border-cyan text-cyan'
                : 'border-transparent text-muted hover:text-primary'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {tab === 'overview' && <OverviewTab portfolio={portfolio} velocity={velocity} health={health} />}
        {tab === 'ready' && <ReadyTab items={readyWork} />}
        {tab === 'blocked' && <BlockedTab items={blockedWork} />}
        {tab === 'delegation' && <DelegationTab data={delegation} />}
        {tab === 'drift' && <DriftTab warnings={drift} />}
      </div>
    </div>
  )
}

function OverviewTab({
  portfolio, velocity, health,
}: {
  portfolio: Record<string, unknown> | undefined
  velocity: Record<string, unknown> | null
  health: Record<string, unknown> | null
}) {
  const h = (health?.health as string) || 'unknown'
  const vel = velocity?.velocity as Record<string, unknown> | undefined

  return (
    <div className="space-y-3">
      {/* Health banner */}
      <SectionCard title="Execution Health">
        <div className="flex items-center gap-3">
          <span className={`text-lg font-mono font-bold uppercase ${HEALTH_COLORS[h] || 'text-muted'}`}>
            {h}
          </span>
          {health?.capability_health && (
            <Badge label={`cap: ${health.capability_health}`} />
          )}
          {typeof health?.goals_at_risk_count === 'number' && health.goals_at_risk_count > 0 && (
            <Badge label={`${health.goals_at_risk_count} goals at risk`} colorClass="text-red-400 bg-red-400/10" />
          )}
        </div>
      </SectionCard>

      {/* Metrics */}
      <SectionCard title="Portfolio Metrics">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Metric label="Total" value={portfolio?.total_work ?? 0} />
          <Metric label="Ready" value={portfolio?.ready ?? 0} />
          <Metric label="Blocked" value={portfolio?.blocked ?? 0} />
          <Metric label="Delegatable" value={portfolio?.delegatable ?? 0} />
        </div>
      </SectionCard>

      {/* Velocity */}
      {vel && (
        <SectionCard title="Velocity">
          <div className="grid grid-cols-2 gap-3">
            <Metric
              label="Completions/day"
              value={(vel.completions_per_day as number)?.toFixed(2) ?? '0'}
              sub="7-day rolling"
            />
            <Metric
              label="Block Rate Δ"
              value={((vel.block_rate_change_7d as number) * 100)?.toFixed(1) + '%' ?? '0%'}
              sub="7-day change"
            />
          </div>
        </SectionCard>
      )}

      {/* Readiness distribution */}
      {portfolio?.by_readiness && (
        <SectionCard title="Readiness Distribution">
          <div className="flex flex-wrap gap-2">
            {Object.entries(portfolio.by_readiness as Record<string, number>).map(([status, count]) => (
              <div key={status} className="flex items-center gap-1">
                <Badge label={status} />
                <span className="text-[10px] font-mono text-primary">{count}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  )
}

function ReadyTab({ items }: { items: Record<string, unknown>[] }) {
  if (!items.length) {
    return (
      <div className="flex items-center gap-2 text-muted text-[10px] font-mono">
        <CheckCircle2 size={14} />
        No ready work items
      </div>
    )
  }
  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={i} className="border border-border rounded-lg p-3 bg-surface-base">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={12} className="text-green-400" />
              <span className="text-xs font-mono text-primary">{item.work_id as string}</span>
            </div>
            <Badge label="ready" />
          </div>
          {item.title && (
            <div className="text-[10px] font-mono text-muted mt-1">{item.title as string}</div>
          )}
          {item.recommended_action && (
            <div className="text-[10px] font-mono text-cyan mt-1">→ {item.recommended_action as string}</div>
          )}
        </div>
      ))}
    </div>
  )
}

function BlockedTab({ items }: { items: Record<string, unknown>[] }) {
  if (!items.length) {
    return (
      <div className="flex items-center gap-2 text-muted text-[10px] font-mono">
        <XCircle size={14} />
        No blocked work items
      </div>
    )
  }
  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={i} className="border border-border rounded-lg p-3 bg-surface-base">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {item.status === 'blocked' ? <XCircle size={12} className="text-red-400" /> :
               item.status === 'waiting_approval' ? <Clock size={12} className="text-yellow-400" /> :
               <AlertTriangle size={12} className="text-orange-400" />}
              <span className="text-xs font-mono text-primary">{item.work_id as string}</span>
            </div>
            <Badge label={item.status as string} />
          </div>
          {item.title && (
            <div className="text-[10px] font-mono text-muted mt-1">{item.title as string}</div>
          )}
          {(item.blocking_reasons as string[])?.length > 0 && (
            <div className="mt-1 space-y-0.5">
              {(item.blocking_reasons as string[]).map((r, j) => (
                <div key={j} className="text-[9px] font-mono text-red-400/80">• {r}</div>
              ))}
            </div>
          )}
          {item.recommended_action && (
            <div className="text-[10px] font-mono text-cyan mt-1">→ {item.recommended_action as string}</div>
          )}
          {item.readiness_score !== undefined && (
            <div className="text-[9px] font-mono text-muted mt-1">
              readiness: {((item.readiness_score as number) * 100).toFixed(0)}%
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function DelegationTab({ data }: { data: Record<string, unknown> | null }) {
  const del = data?.delegation as Record<string, unknown> | undefined
  if (!del) {
    return (
      <div className="flex items-center gap-2 text-muted text-[10px] font-mono">
        <Users size={14} />
        No delegation data
      </div>
    )
  }
  return (
    <div className="space-y-3">
      <SectionCard title="Delegation Feasibility">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <Metric label="Total Assessed" value={del.total_assessed ?? 0} />
          <Metric label="Delegatable" value={del.delegatable ?? 0} />
          <Metric label="Not Delegatable" value={del.not_delegatable ?? 0} />
          <Metric label="Avg Confidence" value={((del.avg_confidence as number) * 100)?.toFixed(0) + '%'} />
          <Metric label="Avg Success Prob" value={((del.avg_success_probability as number) * 100)?.toFixed(0) + '%'} />
        </div>
      </SectionCard>

      {(del.top_missing_capabilities as string[])?.length > 0 && (
        <SectionCard title="Top Missing Capabilities">
          <div className="flex flex-wrap gap-1">
            {(del.top_missing_capabilities as string[]).map((c, i) => (
              <Badge key={i} label={c} colorClass="text-orange-400 bg-orange-400/10" />
            ))}
          </div>
        </SectionCard>
      )}

      {(del.top_risk_factors as string[])?.length > 0 && (
        <SectionCard title="Top Risk Factors">
          <div className="space-y-1">
            {(del.top_risk_factors as string[]).map((r, i) => (
              <div key={i} className="text-[9px] font-mono text-red-400/80">• {r}</div>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  )
}

function DriftTab({ warnings }: { warnings: Record<string, unknown>[] }) {
  if (!warnings.length) {
    return (
      <div className="flex items-center gap-2 text-muted text-[10px] font-mono">
        <TrendingUp size={14} />
        No drift warnings
      </div>
    )
  }
  return (
    <div className="space-y-2">
      {warnings.map((w, i) => (
        <div key={i} className="border border-border rounded-lg p-3 bg-surface-base">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle size={12} className={
                (w.severity as number) >= 0.7 ? 'text-red-400' :
                (w.severity as number) >= 0.4 ? 'text-yellow-400' :
                'text-muted'
              } />
              <span className="text-xs font-mono text-primary">{(w.drift_type as string)?.replace(/_/g, ' ')}</span>
            </div>
            <span className="text-[9px] font-mono text-muted">
              severity: {((w.severity as number) * 100)?.toFixed(0)}%
            </span>
          </div>
          <div className="text-[10px] font-mono text-muted mt-1">{w.description as string}</div>
        </div>
      ))}
    </div>
  )
}
