import { useIntelligenceStore } from '../stores/intelligenceStore'
import { usePolling } from '../hooks/usePolling'

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-danger',
  high: 'text-warn',
  medium: 'text-cyan',
  low: 'text-text-secondary',
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-danger/20 text-danger',
  high: 'bg-warn/20 text-warn',
  medium: 'bg-cyan/20 text-cyan',
  low: 'bg-surface-overlay text-text-secondary',
}

const STATUS_COLORS: Record<string, string> = {
  operational: 'text-ok',
  degraded: 'text-warn',
  limited: 'text-cyan',
  critical: 'text-danger',
}

function ReadinessBar({ label, score, weight }: { label: string; score: number; weight: number }) {
  const color = score >= 80 ? 'bg-ok' : score >= 60 ? 'bg-warn' : score >= 40 ? 'bg-cyan' : 'bg-danger'
  return (
    <div className="flex items-center gap-3">
      <span className="wv-label w-28 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-surface-overlay rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${Math.min(100, score)}%` }} />
      </div>
      <span className="font-mono text-xs w-10 text-right">{score.toFixed(0)}</span>
      <span className="font-mono text-xs text-text-tertiary w-8 text-right">×{weight}</span>
    </div>
  )
}

function ConfidenceDot({ value }: { value: number }) {
  const color = value >= 0.8 ? 'bg-ok' : value >= 0.5 ? 'bg-warn' : 'bg-text-tertiary'
  return (
    <span className={`inline-block w-1.5 h-1.5 rounded-full ${color}`} title={`Confidence: ${(value * 100).toFixed(0)}%`} />
  )
}

export function IntelligencePanel() {
  const data = useIntelligenceStore((s) => s.data)
  const fetchIntelligence = useIntelligenceStore((s) => s.fetchIntelligence)

  usePolling(fetchIntelligence, 15000)

  if (!data) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-text-tertiary text-sm">Loading operational intelligence...</p>
      </div>
    )
  }

  const { bottlenecks, leverage, next_actions, readiness } = data

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Operational Intelligence</h2>
        {readiness?.overall_status && (
          <span className={`font-mono text-xs px-2 py-0.5 rounded uppercase ${STATUS_COLORS[readiness.overall_status] || 'text-text-secondary'}`}>
            {readiness.overall_status} — {readiness.composite_score?.toFixed(0) ?? '?'}/100
          </span>
        )}
      </div>

      {/* Readiness Scores */}
      <section>
        <h3 className="wv-label mb-3">System Readiness</h3>
        <div className="wv-card p-3 space-y-2">
          {readiness?.dimensions && Object.values(readiness.dimensions).length > 0 ? (
            Object.values(readiness.dimensions)
              .sort((a, b) => a.score - b.score)
              .map((dim) => (
                <div key={dim.dimension}>
                  <ReadinessBar
                    label={dim.dimension.replace(/_/g, ' ')}
                    score={dim.score}
                    weight={dim.weight}
                  />
                  <p className="text-xs text-text-tertiary ml-[7.5rem] mt-0.5">{dim.explanation}</p>
                </div>
              ))
          ) : (
            <p className="text-xs text-text-tertiary">Not yet computed</p>
          )}
        </div>
      </section>

      {/* Current Bottlenecks */}
      <section>
        <h3 className="wv-label mb-3">
          Current Bottlenecks
          {bottlenecks?.active_count > 0 && (
            <span className="ml-2 font-mono text-xs text-warn">{bottlenecks.active_count}</span>
          )}
        </h3>
        {bottlenecks?.active && bottlenecks.active.length > 0 ? (
          <div className="space-y-2">
            {bottlenecks.active.map((bn) => (
              <div key={bn.bottleneck_id} className="wv-card p-3">
                <div className="flex items-start gap-2">
                  <ConfidenceDot value={bn.confidence} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`font-mono text-xs uppercase ${SEVERITY_COLORS[bn.severity]}`}>
                        {bn.severity}
                      </span>
                      <span className="font-mono text-xs text-text-tertiary">{bn.category.replace(/_/g, ' ')}</span>
                      {bn.recurrence_count > 1 && (
                        <span className="font-mono text-xs text-warn">×{bn.recurrence_count}</span>
                      )}
                    </div>
                    <p className="text-sm">{bn.description}</p>
                    {bn.evidence?.length > 0 && (
                      <div className="mt-1.5 space-y-0.5">
                        {bn.evidence.map((ev, i) => (
                          <p key={i} className="text-xs text-text-tertiary font-mono">
                            {ev.signal}: {ev.observed}{ev.expected ? ` (expected ${ev.expected})` : ''}
                          </p>
                        ))}
                      </div>
                    )}
                    {bn.recommendation && (
                      <p className="text-xs text-cyan mt-1.5">{bn.recommendation}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-ok font-mono">No active bottlenecks</p>
        )}
      </section>

      {/* Highest Leverage Actions */}
      <section>
        <h3 className="wv-label mb-3">Highest Leverage Actions</h3>
        {leverage?.top_opportunities && leverage.top_opportunities.length > 0 ? (
          <div className="space-y-2">
            {leverage.top_opportunities.map((opp, idx) => (
              <div key={opp.opportunity_id} className="wv-card p-3">
                <div className="flex items-start gap-2">
                  <span className="font-mono text-xs text-cyan shrink-0 mt-0.5">#{idx + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{opp.action}</p>
                    <p className="text-xs text-text-secondary mt-0.5">{opp.impact_description}</p>
                    <div className="flex items-center gap-3 mt-1.5">
                      <span className="font-mono text-xs text-text-tertiary">
                        Impact: {(opp.impact_score * 100).toFixed(0)}%
                      </span>
                      <ConfidenceDot value={opp.confidence} />
                      <span className="font-mono text-xs text-text-tertiary">
                        {(opp.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                    {opp.evidence?.length > 0 && (
                      <div className="mt-1.5">
                        {opp.evidence.map((ev, i) => (
                          <p key={i} className="text-xs text-text-tertiary font-mono">
                            {ev.source}: {ev.detail}
                          </p>
                        ))}
                      </div>
                    )}
                    {opp.reasoning && (
                      <p className="text-xs text-text-secondary mt-1 italic">{opp.reasoning}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-tertiary">No leverage opportunities computed yet</p>
        )}
      </section>

      {/* Next Recommended Actions */}
      <section>
        <h3 className="wv-label mb-3">Next Recommended Actions</h3>
        {next_actions?.actions && next_actions.actions.length > 0 ? (
          <div className="space-y-1.5">
            {next_actions.actions.map((act) => (
              <div key={act.action_id} className="wv-card flex items-start gap-3 p-3">
                <span className={`font-mono text-xs px-1.5 py-0.5 rounded uppercase shrink-0 ${PRIORITY_COLORS[act.priority]}`}>
                  {act.priority}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm">{act.action}</p>
                  <p className="text-xs text-text-secondary mt-0.5">{act.reason}</p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="font-mono text-xs text-text-tertiary">{act.category}</span>
                    {act.estimated_effort && (
                      <span className="font-mono text-xs text-text-tertiary">~{act.estimated_effort}</span>
                    )}
                  </div>
                  {act.evidence?.length > 0 && (
                    <div className="mt-1">
                      {act.evidence.map((ev, i) => (
                        <p key={i} className="text-xs text-text-tertiary font-mono">
                          {ev.source}: {ev.detail}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-tertiary">No actions recommended — system idle</p>
        )}
      </section>
    </div>
  )
}
