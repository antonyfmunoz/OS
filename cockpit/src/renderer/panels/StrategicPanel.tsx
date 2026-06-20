import { useEffect, useState } from 'react'
import {
  Compass,
  RefreshCw,
  AlertTriangle,
  ArrowUpCircle,
  Shield,
  FileText,
  TrendingDown,
  CheckCircle2,
} from 'lucide-react'
import { useStrategicStore } from '../stores/strategicStore'

type Tab = 'overview' | 'priorities' | 'risks' | 'drift' | 'recommendations' | 'brief'

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-400/10',
  high: 'text-orange-400 bg-orange-400/10',
  alert: 'text-orange-400 bg-orange-400/10',
  medium: 'text-yellow-400 bg-yellow-400/10',
  warning: 'text-yellow-400 bg-yellow-400/10',
  low: 'text-text-tertiary bg-surface-raised',
  healthy: 'text-green-400 bg-green-400/10',
  watch: 'text-yellow-400 bg-yellow-400/10',
  degraded: 'text-orange-400 bg-orange-400/10',
}

function Badge({ text, color }: { text: string; color?: string }) {
  const cls = color ?? SEVERITY_COLORS[text.toLowerCase()] ?? 'text-text-tertiary bg-surface-raised'
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-mono ${cls}`}>
      {text.toUpperCase()}
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

function OverviewTab() {
  const { context, brief } = useStrategicStore()

  const health = (context as Record<string, unknown>)?.health as string ?? 'unknown'
  const situation = (brief as Record<string, unknown>)?.situation as string ?? '—'
  const priorities = ((brief as Record<string, unknown>)?.priorities as string[]) ?? []
  const blockers = ((brief as Record<string, unknown>)?.blockers as string[]) ?? []
  const risks = ((brief as Record<string, unknown>)?.risks as string[]) ?? []
  const driftWarnings = ((brief as Record<string, unknown>)?.drift_warnings as string[]) ?? []

  return (
    <div className="space-y-3">
      <SectionCard>
        <div className="flex items-center gap-2 mb-2">
          <Compass className="w-4 h-4 text-cyan" />
          <span className="text-sm font-medium text-text-primary">Health</span>
          <Badge text={health} />
        </div>
        <p className="text-xs text-text-secondary">{situation}</p>
      </SectionCard>

      <div className="grid grid-cols-2 gap-2">
        <SectionCard>
          <div className="text-xs text-text-tertiary mb-1">Priorities</div>
          <div className="text-lg font-mono text-text-primary">{priorities.length}</div>
        </SectionCard>
        <SectionCard>
          <div className="text-xs text-text-tertiary mb-1">Blockers</div>
          <div className="text-lg font-mono text-text-primary">{blockers.length}</div>
        </SectionCard>
        <SectionCard>
          <div className="text-xs text-text-tertiary mb-1">Risks</div>
          <div className="text-lg font-mono text-text-primary">{risks.length}</div>
        </SectionCard>
        <SectionCard>
          <div className="text-xs text-text-tertiary mb-1">Drift</div>
          <div className="text-lg font-mono text-text-primary">{driftWarnings.length}</div>
        </SectionCard>
      </div>
    </div>
  )
}

function PrioritiesTab() {
  const { priorities } = useStrategicStore()

  if (!priorities.length) {
    return <p className="text-xs text-text-tertiary">No priorities detected.</p>
  }

  return (
    <div className="space-y-2">
      {priorities.map((p, i) => {
        const title = (p.title as string) ?? 'Untitled'
        const score = (p.score as number) ?? 0
        const source = (p.source as string) ?? ''
        const rationale = (p.rationale as string) ?? ''
        return (
          <SectionCard key={i}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-text-primary font-medium">{title}</span>
              <span className="text-xs font-mono text-cyan">{score.toFixed(2)}</span>
            </div>
            {rationale && (
              <p className="text-xs text-text-secondary mb-1">{rationale}</p>
            )}
            {source && <Badge text={source} />}
            <div className="mt-1 h-1 rounded bg-surface-raised overflow-hidden">
              <div
                className="h-full bg-cyan rounded"
                style={{ width: `${Math.min(score * 100, 100)}%` }}
              />
            </div>
          </SectionCard>
        )
      })}
    </div>
  )
}

function RisksTab() {
  const { risks } = useStrategicStore()

  if (!risks.length) {
    return <p className="text-xs text-text-tertiary">No risks detected.</p>
  }

  return (
    <div className="space-y-2">
      {risks.map((r, i) => {
        const title = (r.title as string) ?? 'Untitled'
        const severity = (r.severity as string) ?? 'medium'
        const category = (r.category as string) ?? ''
        const description = (r.description as string) ?? ''
        const riskScore = (r.risk_score as number) ?? 0
        return (
          <SectionCard key={i}>
            <div className="flex items-center gap-2 mb-1">
              <Shield className="w-3 h-3 text-text-tertiary" />
              <span className="text-sm text-text-primary">{title}</span>
              <Badge text={severity} />
            </div>
            {description && (
              <p className="text-xs text-text-secondary mb-1">{description}</p>
            )}
            <div className="flex items-center gap-2">
              {category && <Badge text={category} color="text-text-tertiary bg-surface-raised" />}
              <span className="text-xs font-mono text-text-tertiary">
                score: {riskScore.toFixed(2)}
              </span>
            </div>
          </SectionCard>
        )
      })}
    </div>
  )
}

function DriftTab() {
  const { driftWarnings } = useStrategicStore()

  if (!driftWarnings.length) {
    return <p className="text-xs text-text-tertiary">No drift detected.</p>
  }

  return (
    <div className="space-y-2">
      {driftWarnings.map((d, i) => {
        const title = (d.title as string) ?? 'Untitled'
        const severity = (d.severity as string) ?? 'warning'
        const driftType = (d.drift_type as string) ?? ''
        const daysStagnant = (d.days_stagnant as number) ?? 0
        const description = (d.description as string) ?? ''
        return (
          <SectionCard key={i}>
            <div className="flex items-center gap-2 mb-1">
              <TrendingDown className="w-3 h-3 text-text-tertiary" />
              <span className="text-sm text-text-primary">{title}</span>
              <Badge text={severity} />
            </div>
            {description && (
              <p className="text-xs text-text-secondary mb-1">{description}</p>
            )}
            <div className="flex items-center gap-2">
              {driftType && <Badge text={driftType} color="text-text-tertiary bg-surface-raised" />}
              {daysStagnant > 0 && (
                <span className="text-xs font-mono text-text-tertiary">
                  {daysStagnant}d stagnant
                </span>
              )}
            </div>
          </SectionCard>
        )
      })}
    </div>
  )
}

function RecommendationsTab() {
  const { recommendations } = useStrategicStore()

  if (!recommendations.length) {
    return <p className="text-xs text-text-tertiary">No recommendations.</p>
  }

  return (
    <div className="space-y-2">
      {recommendations.map((r, i) => {
        const action = (r.action as string) ?? 'Untitled'
        const reason = (r.reason as string) ?? ''
        const confidence = (r.confidence as number) ?? 0
        const source = (r.source as string) ?? ''
        const priorityScore = (r.priority_score as number) ?? 0
        return (
          <SectionCard key={i}>
            <div className="flex items-center gap-2 mb-1">
              <ArrowUpCircle className="w-3 h-3 text-cyan" />
              <span className="text-sm text-text-primary">{action}</span>
            </div>
            {reason && (
              <p className="text-xs text-text-secondary mb-1">{reason}</p>
            )}
            <div className="flex items-center gap-2">
              {source && <Badge text={source} color="text-text-tertiary bg-surface-raised" />}
              <span className="text-xs font-mono text-text-tertiary">
                conf: {confidence.toFixed(2)} | pri: {priorityScore.toFixed(2)}
              </span>
            </div>
          </SectionCard>
        )
      })}
    </div>
  )
}

function BriefTab() {
  const { brief } = useStrategicStore()

  if (!brief) {
    return <p className="text-xs text-text-tertiary">Loading brief...</p>
  }

  const health = (brief.health as string) ?? 'unknown'
  const situation = (brief.situation as string) ?? ''
  const progress = (brief.progress as string[]) ?? []
  const blockers = (brief.blockers as string[]) ?? []
  const risks = (brief.risks as string[]) ?? []
  const priorities = (brief.priorities as string[]) ?? []
  const recommendations = (brief.recommendations as string[]) ?? []
  const driftWarnings = (brief.drift_warnings as string[]) ?? []

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <FileText className="w-4 h-4 text-cyan" />
        <span className="text-sm font-medium text-text-primary">Executive Brief</span>
        <Badge text={health} />
      </div>

      {situation && (
        <SectionCard>
          <div className="text-xs text-text-tertiary mb-1">Situation</div>
          <p className="text-sm text-text-primary">{situation}</p>
        </SectionCard>
      )}

      {progress.length > 0 && (
        <SectionCard>
          <div className="text-xs text-text-tertiary mb-1">Progress</div>
          {progress.map((p, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs text-text-secondary">
              <CheckCircle2 className="w-3 h-3 text-green-400" />
              {p}
            </div>
          ))}
        </SectionCard>
      )}

      {blockers.length > 0 && (
        <SectionCard>
          <div className="text-xs text-text-tertiary mb-1">Blockers</div>
          {blockers.map((b, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs text-red-400">
              <AlertTriangle className="w-3 h-3" />
              {b}
            </div>
          ))}
        </SectionCard>
      )}

      {risks.length > 0 && (
        <SectionCard>
          <div className="text-xs text-text-tertiary mb-1">Risks</div>
          {risks.map((r, i) => (
            <div key={i} className="text-xs text-text-secondary">{r}</div>
          ))}
        </SectionCard>
      )}

      {priorities.length > 0 && (
        <SectionCard>
          <div className="text-xs text-text-tertiary mb-1">Priorities</div>
          {priorities.map((p, i) => (
            <div key={i} className="text-xs text-text-secondary">
              {i + 1}. {p}
            </div>
          ))}
        </SectionCard>
      )}

      {driftWarnings.length > 0 && (
        <SectionCard>
          <div className="text-xs text-text-tertiary mb-1">Drift</div>
          {driftWarnings.map((d, i) => (
            <div key={i} className="text-xs text-text-secondary">{d}</div>
          ))}
        </SectionCard>
      )}

      {recommendations.length > 0 && (
        <SectionCard>
          <div className="text-xs text-text-tertiary mb-1">Recommended Actions</div>
          {recommendations.map((r, i) => (
            <div key={i} className="text-xs text-cyan">&gt; {r}</div>
          ))}
        </SectionCard>
      )}
    </div>
  )
}

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'priorities', label: 'Priorities' },
  { id: 'risks', label: 'Risks' },
  { id: 'drift', label: 'Drift' },
  { id: 'recommendations', label: 'Actions' },
  { id: 'brief', label: 'Brief' },
]

export function StrategicPanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const {
    loading,
    fetchContext,
    fetchPriorities,
    fetchRisks,
    fetchRecommendations,
    fetchDrift,
    fetchBrief,
  } = useStrategicStore()

  useEffect(() => {
    fetchContext()
    fetchPriorities()
    fetchRisks()
    fetchRecommendations()
    fetchDrift()
    fetchBrief()
  }, [])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-cyan" />
          <span className="text-sm font-medium text-text-primary">Strategic</span>
        </div>
        <button
          className="p-1 rounded hover:bg-surface-hover text-text-tertiary"
          onClick={() => {
            fetchContext()
            fetchPriorities()
            fetchRisks()
            fetchRecommendations()
            fetchDrift()
            fetchBrief()
          }}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Tab Bar */}
      <div className="flex border-b border-border px-2 shrink-0">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`px-3 py-1.5 text-xs border-b-2 transition-colors ${
              tab === t.id
                ? 'border-cyan text-cyan'
                : 'border-transparent text-text-tertiary hover:text-text-secondary'
            }`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {tab === 'overview' && <OverviewTab />}
        {tab === 'priorities' && <PrioritiesTab />}
        {tab === 'risks' && <RisksTab />}
        {tab === 'drift' && <DriftTab />}
        {tab === 'recommendations' && <RecommendationsTab />}
        {tab === 'brief' && <BriefTab />}
      </div>
    </div>
  )
}
