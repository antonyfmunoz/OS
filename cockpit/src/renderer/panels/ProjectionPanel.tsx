import { useEffect, useState, useCallback } from 'react'
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Lightbulb,
  BarChart3,
  Play,
  RefreshCw,
  Clock,
  Target,
  Shield,
  Zap,
  ChevronRight,
  Eye,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from 'lucide-react'
import { useOperatorLoopStore } from '../stores/operatorLoopStore'
import type {
  ProjectionTrend,
  ProjectionData,
  ProjectionRisk,
  ProjectionOpportunity,
  ProjectionAccuracy,
} from '../stores/operatorLoopStore'

type Tab = 'overview' | 'trends' | 'risks' | 'opportunities' | 'accuracy'

const HORIZON_LABELS: Record<string, string> = {
  '24h': '24 Hours',
  '7d': '7 Days',
  '30d': '30 Days',
  '90d': '90 Days',
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-400/10 border-red-400/30',
  high: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
  medium: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
  low: 'text-text-tertiary bg-surface-raised border-border',
}

const CONFIDENCE_COLORS: Record<string, string> = {
  high: 'text-green-400 bg-green-400/10',
  medium: 'text-yellow-400 bg-yellow-400/10',
  low: 'text-orange-400 bg-orange-400/10',
  speculative: 'text-red-400 bg-red-400/10',
}

const DIRECTION_ICONS: Record<string, typeof TrendingUp> = {
  positive: ArrowUpRight,
  negative: ArrowDownRight,
  stagnant: Minus,
  accelerating: TrendingUp,
  decelerating: TrendingDown,
}

const DIRECTION_COLORS: Record<string, string> = {
  positive: 'text-green-400',
  negative: 'text-red-400',
  stagnant: 'text-text-tertiary',
  accelerating: 'text-cyan',
  decelerating: 'text-orange-400',
}

function KpiCard({ label, value, icon: Icon, color = 'text-text-primary' }: {
  label: string; value: string | number; icon: typeof TrendingUp; color?: string
}) {
  return (
    <div className="bg-surface-raised border border-border rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-xs text-text-tertiary">{label}</span>
      </div>
      <span className={`text-lg font-mono font-bold ${color}`}>{value}</span>
    </div>
  )
}

function OverviewTab({
  projections,
  trends,
  risks,
  opportunities,
  accuracy,
  lastRunAt,
}: {
  projections: ProjectionData[]
  trends: ProjectionTrend[]
  risks: ProjectionRisk[]
  opportunities: ProjectionOpportunity[]
  accuracy: ProjectionAccuracy | null
  lastRunAt: number
}) {
  const criticalRisks = risks.filter(r => r.severity === 'critical' || r.severity === 'high')
  const uniqueDomains = new Set(projections.map(p => p.domain))

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Domains" value={uniqueDomains.size} icon={Target} color="text-cyan" />
        <KpiCard label="Trends" value={trends.length} icon={TrendingUp} color="text-blue-400" />
        <KpiCard label="Risks" value={risks.length} icon={Shield} color={criticalRisks.length > 0 ? 'text-red-400' : 'text-yellow-400'} />
        <KpiCard label="Opportunities" value={opportunities.length} icon={Lightbulb} color="text-green-400" />
      </div>

      {lastRunAt > 0 && (
        <div className="text-[10px] text-text-tertiary font-mono">
          Last projection: {new Date(lastRunAt * 1000).toLocaleString()}
          {accuracy && ` · Accuracy: ${(accuracy.accuracy_rate * 100).toFixed(0)}% (${accuracy.total_projections} tracked)`}
        </div>
      )}

      {criticalRisks.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono text-red-400 uppercase tracking-wider">Critical / High Risks</span>
          {criticalRisks.map(r => (
            <div key={r.risk_id} className={`p-3 rounded-lg border ${SEVERITY_COLORS[r.severity]}`}>
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle size={12} />
                <span className="text-xs font-medium">{r.title}</span>
                <span className="ml-auto text-[10px] font-mono">{r.probability.toFixed(0)}% prob</span>
              </div>
              <p className="text-[10px] text-text-secondary">{r.impact}</p>
              <p className="text-[10px] text-text-tertiary mt-1">{r.mitigation}</p>
            </div>
          ))}
        </div>
      )}

      {opportunities.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono text-green-400 uppercase tracking-wider">Opportunities</span>
          {opportunities.slice(0, 3).map(o => (
            <div key={o.opportunity_id} className="p-3 rounded-lg border border-green-400/20 bg-green-400/5">
              <div className="flex items-center gap-2 mb-1">
                <Lightbulb size={12} className="text-green-400" />
                <span className="text-xs font-medium text-green-400">{o.title}</span>
              </div>
              <p className="text-[10px] text-text-secondary">{o.action_suggestion}</p>
            </div>
          ))}
        </div>
      )}

      {trends.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono text-blue-400 uppercase tracking-wider">Active Trends</span>
          {trends.slice(0, 5).map(t => {
            const DirIcon = DIRECTION_ICONS[t.direction] || Minus
            const dirColor = DIRECTION_COLORS[t.direction] || 'text-text-tertiary'
            return (
              <div key={t.trend_id} className="flex items-center gap-3 p-2 bg-surface-raised rounded-lg border border-border">
                <DirIcon size={14} className={dirColor} />
                <div className="flex-1 min-w-0">
                  <span className="text-xs text-text-primary">{t.domain}</span>
                  <span className="text-[10px] text-text-tertiary ml-2">{t.metric}</span>
                </div>
                <span className={`text-xs font-mono ${dirColor}`}>
                  {t.magnitude >= 0 ? '+' : ''}{(t.magnitude * 100).toFixed(0)}%
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function TrendsTab({ trends }: { trends: ProjectionTrend[] }) {
  if (trends.length === 0) {
    return <div className="p-4 text-sm text-text-tertiary">No trends detected. Run projections first.</div>
  }

  return (
    <div className="p-4 space-y-2 overflow-y-auto h-full">
      {trends.map(t => {
        const DirIcon = DIRECTION_ICONS[t.direction] || Minus
        const dirColor = DIRECTION_COLORS[t.direction] || 'text-text-tertiary'
        return (
          <div key={t.trend_id} className="p-3 bg-surface-raised rounded-lg border border-border">
            <div className="flex items-center gap-2 mb-1">
              <DirIcon size={14} className={dirColor} />
              <span className="text-xs font-medium text-text-primary">{t.domain}</span>
              <span className="text-[10px] font-mono text-text-tertiary">{t.metric}</span>
              <span className={`ml-auto text-xs font-mono ${dirColor}`}>
                {t.magnitude >= 0 ? '+' : ''}{(t.magnitude * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-[10px] text-text-secondary">{t.description}</p>
            <div className="flex gap-3 mt-1">
              <span className="text-[10px] text-text-tertiary">{t.data_points} data points</span>
              {t.period_days > 0 && <span className="text-[10px] text-text-tertiary">{t.period_days.toFixed(0)}d window</span>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function RisksTab({ risks }: { risks: ProjectionRisk[] }) {
  if (risks.length === 0) {
    return <div className="p-4 text-sm text-text-tertiary">No risks detected. Run projections first.</div>
  }

  return (
    <div className="p-4 space-y-2 overflow-y-auto h-full">
      {risks.map(r => (
        <div key={r.risk_id} className={`p-3 rounded-lg border ${SEVERITY_COLORS[r.severity]}`}>
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle size={12} />
            <span className="text-xs font-medium">{r.title}</span>
            <span className={`ml-auto text-[10px] font-mono px-2 py-0.5 rounded ${SEVERITY_COLORS[r.severity]}`}>
              {r.severity}
            </span>
          </div>
          <p className="text-[10px] text-text-secondary mb-1">{r.impact}</p>
          <div className="flex items-center gap-3 text-[10px]">
            <span className="text-text-tertiary">Probability: {(r.probability * 100).toFixed(0)}%</span>
            <span className="text-text-tertiary">Horizon: {HORIZON_LABELS[r.horizon] || r.horizon}</span>
            <span className="text-text-tertiary">Type: {r.risk_type}</span>
          </div>
          {r.evidence.length > 0 && (
            <div className="mt-2 space-y-0.5">
              {r.evidence.map((e, i) => (
                <div key={i} className="flex items-start gap-1.5">
                  <ChevronRight size={10} className="mt-0.5 text-text-tertiary shrink-0" />
                  <span className="text-[10px] text-text-tertiary">{e}</span>
                </div>
              ))}
            </div>
          )}
          {r.mitigation && (
            <p className="text-[10px] text-cyan mt-1">Mitigation: {r.mitigation}</p>
          )}
        </div>
      ))}
    </div>
  )
}

function OpportunitiesTab({ opportunities }: { opportunities: ProjectionOpportunity[] }) {
  if (opportunities.length === 0) {
    return <div className="p-4 text-sm text-text-tertiary">No opportunities detected. Run projections first.</div>
  }

  return (
    <div className="p-4 space-y-2 overflow-y-auto h-full">
      {opportunities.map(o => (
        <div key={o.opportunity_id} className="p-3 rounded-lg border border-green-400/20 bg-green-400/5">
          <div className="flex items-center gap-2 mb-1">
            <Lightbulb size={12} className="text-green-400" />
            <span className="text-xs font-medium text-green-400">{o.title}</span>
            <span className={`ml-auto text-[10px] font-mono px-2 py-0.5 rounded ${CONFIDENCE_COLORS[o.confidence]}`}>
              {o.confidence}
            </span>
          </div>
          <p className="text-[10px] text-text-secondary mb-1">{o.potential_impact}</p>
          <p className="text-[10px] text-cyan">{o.action_suggestion}</p>
          <div className="flex items-center gap-3 mt-1 text-[10px] text-text-tertiary">
            <span>Domain: {o.domain}</span>
            <span>Type: {o.opportunity_type}</span>
            <span>Horizon: {HORIZON_LABELS[o.horizon] || o.horizon}</span>
          </div>
          {o.evidence.length > 0 && (
            <div className="mt-1 space-y-0.5">
              {o.evidence.map((e, i) => (
                <div key={i} className="flex items-start gap-1.5">
                  <ChevronRight size={10} className="mt-0.5 text-text-tertiary shrink-0" />
                  <span className="text-[10px] text-text-tertiary">{e}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function AccuracyTab({ accuracy }: { accuracy: ProjectionAccuracy | null }) {
  if (!accuracy || accuracy.total_projections === 0) {
    return <div className="p-4 text-sm text-text-tertiary">No projection outcomes recorded yet.</div>
  }

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Total Tracked" value={accuracy.total_projections} icon={BarChart3} color="text-cyan" />
        <KpiCard label="Accurate" value={accuracy.accurate_count} icon={Target} color="text-green-400" />
        <KpiCard
          label="Accuracy Rate"
          value={`${(accuracy.accuracy_rate * 100).toFixed(0)}%`}
          icon={Eye}
          color={accuracy.accuracy_rate >= 0.7 ? 'text-green-400' : accuracy.accuracy_rate >= 0.5 ? 'text-yellow-400' : 'text-red-400'}
        />
        <KpiCard label="Avg Score" value={accuracy.avg_score.toFixed(2)} icon={Zap} color="text-blue-400" />
      </div>

      {Object.keys(accuracy.by_domain).length > 0 && (
        <div>
          <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">By Domain</span>
          <div className="mt-2 space-y-1">
            {Object.entries(accuracy.by_domain).map(([domain, stats]) => (
              <div key={domain} className="flex items-center gap-3 p-2 bg-surface-raised rounded border border-border">
                <span className="text-xs text-text-primary w-28 truncate">{domain}</span>
                <span className="text-[10px] font-mono text-text-tertiary">{stats.total_projections} proj</span>
                <span className={`text-[10px] font-mono ${stats.accuracy_rate >= 0.7 ? 'text-green-400' : 'text-yellow-400'}`}>
                  {(stats.accuracy_rate * 100).toFixed(0)}%
                </span>
                <span className="text-[10px] font-mono text-text-tertiary ml-auto">avg {stats.avg_score.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.keys(accuracy.by_horizon).length > 0 && (
        <div>
          <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">By Horizon</span>
          <div className="mt-2 space-y-1">
            {Object.entries(accuracy.by_horizon).map(([horizon, stats]) => (
              <div key={horizon} className="flex items-center gap-3 p-2 bg-surface-raised rounded border border-border">
                <span className="text-xs text-text-primary w-28">{HORIZON_LABELS[horizon] || horizon}</span>
                <span className="text-[10px] font-mono text-text-tertiary">{stats.total_projections} proj</span>
                <span className={`text-[10px] font-mono ${stats.accuracy_rate >= 0.7 ? 'text-green-400' : 'text-yellow-400'}`}>
                  {(stats.accuracy_rate * 100).toFixed(0)}%
                </span>
                <span className="text-[10px] font-mono text-text-tertiary ml-auto">avg {stats.avg_score.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function ProjectionPanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const {
    projectionState, projectionTrends, projectionRisks, projectionOpportunities,
    projectionAccuracy, projectionLoading,
    fetchProjectionState, runProjections, fetchProjectionAccuracy,
  } = useOperatorLoopStore()

  useEffect(() => {
    fetchProjectionState()
    fetchProjectionAccuracy()
  }, [])

  const handleRun = useCallback(async () => {
    await runProjections()
  }, [runProjections])

  const lastRunAt = projectionState?.last_run_at ?? 0

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <TrendingUp size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Projection Engine</span>
        </div>
        <button
          onClick={handleRun}
          disabled={projectionLoading}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          {projectionLoading ? <RefreshCw size={10} className="animate-spin" /> : <Play size={10} />}
          {projectionLoading ? 'Running...' : 'Run Projections'}
        </button>
      </div>

      <div className="flex border-b border-border shrink-0">
        {(['overview', 'trends', 'risks', 'opportunities', 'accuracy'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider border-b-2 transition-colors ${
              tab === t
                ? 'border-cyan text-cyan'
                : 'border-transparent text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t}
            {t === 'risks' && projectionRisks.length > 0 && (
              <span className="ml-1 text-red-400">({projectionRisks.length})</span>
            )}
            {t === 'opportunities' && projectionOpportunities.length > 0 && (
              <span className="ml-1 text-green-400">({projectionOpportunities.length})</span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-hidden">
        {tab === 'overview' && (
          <OverviewTab
            projections={projectionState?.projections ?? []}
            trends={projectionTrends}
            risks={projectionRisks}
            opportunities={projectionOpportunities}
            accuracy={projectionAccuracy}
            lastRunAt={lastRunAt}
          />
        )}
        {tab === 'trends' && <TrendsTab trends={projectionTrends} />}
        {tab === 'risks' && <RisksTab risks={projectionRisks} />}
        {tab === 'opportunities' && <OpportunitiesTab opportunities={projectionOpportunities} />}
        {tab === 'accuracy' && <AccuracyTab accuracy={projectionAccuracy} />}
      </div>
    </div>
  )
}
