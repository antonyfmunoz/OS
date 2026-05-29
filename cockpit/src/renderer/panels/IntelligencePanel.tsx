import { useIntelligenceStore } from '../stores/intelligenceStore'
import { useCoherenceStore } from '../stores/coherenceStore'
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

function TemplateStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    raw: 'bg-surface-overlay text-text-tertiary',
    candidate: 'bg-cyan/20 text-cyan',
    approved: 'bg-ok/20 text-ok',
    promoted: 'bg-ok text-surface',
    rejected: 'bg-danger/20 text-danger',
    superseded: 'bg-surface-overlay text-text-tertiary',
    deprecated: 'bg-surface-overlay text-text-tertiary',
  }
  return (
    <span className={`font-mono text-xs px-1.5 py-0.5 rounded uppercase ${colors[status] || 'bg-surface-overlay text-text-secondary'}`}>
      {status}
    </span>
  )
}

function PropagationStatusDot({ status }: { status: string }) {
  const color = status === 'completed' ? 'bg-ok' : status === 'failed' ? 'bg-danger' : 'bg-warn'
  return <span className={`inline-block w-2 h-2 rounded-full ${color}`} />
}

export function IntelligencePanel() {
  const data = useIntelligenceStore((s) => s.data)
  const fetchIntelligence = useIntelligenceStore((s) => s.fetchIntelligence)
  const coherence = useCoherenceStore()
  const fetchCoherence = useCoherenceStore((s) => s.fetchAll)

  usePolling(fetchIntelligence, 15000)
  usePolling(fetchCoherence, 20000)

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

      {/* ── Phase 9.7: Autonomous PR Factory ── */}
      <section>
        <h3 className="wv-label mb-3">
          Autonomous PR Factory
          {coherence.prFactory && (
            <span className="ml-2 font-mono text-xs text-cyan">
              {coherence.prFactory.sandbox_manager.active_sandboxes} active / {coherence.prFactory.pr_created_count} PRs
            </span>
          )}
        </h3>
        {coherence.prFactory ? (
          <div className="space-y-2">
            <div className="wv-card p-3 space-y-1">
              <div className="flex items-center gap-3">
                <span className="wv-label w-40">Active sandboxes</span>
                <span className="font-mono text-xs">{coherence.prFactory.sandbox_manager.active_sandboxes} / {coherence.prFactory.sandbox_manager.max_parallel}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="wv-label w-40">Total PRs created</span>
                <span className="font-mono text-xs text-ok">{coherence.prFactory.pr_created_count}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="wv-label w-40">Blocked</span>
                <span className="font-mono text-xs text-warn">{coherence.prFactory.blocked_count}</span>
              </div>
              {coherence.prFactory.failed_count > 0 && (
                <div className="flex items-center gap-3">
                  <span className="wv-label w-40">Failed</span>
                  <span className="font-mono text-xs text-danger">{coherence.prFactory.failed_count}</span>
                </div>
              )}
              {Object.keys(coherence.prFactory.sandbox_manager.file_locks).length > 0 && (
                <div className="mt-2">
                  <p className="text-xs text-text-tertiary mb-1">File locks:</p>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(coherence.prFactory.sandbox_manager.file_locks).map(([file, owner]) => (
                      <span key={file} className="text-xs font-mono bg-warn/10 text-warn px-1.5 py-0.5 rounded" title={`Locked by ${owner}`}>
                        {file.split('/').pop()}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {coherence.prFactory.sandbox_manager.sandboxes.length > 0 && (
              <div className="space-y-1.5">
                {coherence.prFactory.sandbox_manager.sandboxes.slice(-5).reverse().map((sb) => (
                  <div key={sb.sandbox_id} className="wv-card p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`font-mono text-xs px-1.5 py-0.5 rounded uppercase ${
                        sb.status === 'pr_created' ? 'bg-ok/20 text-ok' :
                        sb.status === 'merged' ? 'bg-cyan/20 text-cyan' :
                        sb.status === 'executing' ? 'bg-warn/20 text-warn' :
                        sb.status === 'abandoned' || sb.status === 'validation_failed' ? 'bg-danger/20 text-danger' :
                        'bg-surface-overlay text-text-secondary'
                      }`}>
                        {sb.status}
                      </span>
                      <span className="font-mono text-xs text-text-tertiary">{sb.sandbox_id}</span>
                      {sb.pr_number > 0 && (
                        <span className="font-mono text-xs text-ok">PR #{sb.pr_number}</span>
                      )}
                    </div>
                    <p className="text-xs font-mono text-text-secondary">{sb.branch_name}</p>
                    {sb.affected_files.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {sb.affected_files.map((f) => (
                          <span key={f} className="text-xs font-mono bg-surface-overlay px-1 py-0.5 rounded">
                            {f.split('/').pop()}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-text-tertiary">PR factory not initialized</p>
        )}
      </section>

      {/* ── Phase 9.8: Autonomous Cadence ── */}
      <section>
        <h3 className="wv-label mb-3">
          Autonomous Cadence
          {coherence.cadence && (
            <span className="ml-2 font-mono text-xs text-cyan">
              {coherence.cadence.mode}
            </span>
          )}
        </h3>
        {coherence.cadence ? (
          <div className="wv-card p-3 space-y-1">
            <div className="flex items-center gap-3">
              <span className="wv-label w-40">Mode</span>
              <span className={`font-mono text-xs px-1.5 py-0.5 rounded uppercase ${
                coherence.cadence.mode === 'off' ? 'bg-surface-overlay text-text-secondary' :
                coherence.cadence.mode === 'dry_run_only' ? 'bg-cyan/20 text-cyan' :
                'bg-warn/20 text-warn'
              }`}>{coherence.cadence.mode}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="wv-label w-40">Dry runs today</span>
              <span className="font-mono text-xs">{coherence.cadence.dry_runs_today}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="wv-label w-40">PRs today</span>
              <span className="font-mono text-xs">{coherence.cadence.prs_today}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="wv-label w-40">Total runs</span>
              <span className="font-mono text-xs">{coherence.cadence.total_runs}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="wv-label w-40">Pending recs</span>
              <span className="font-mono text-xs">{coherence.cadence.pending_recommendations}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="wv-label w-40">Should run</span>
              <span className={`font-mono text-xs ${coherence.cadence.should_run ? 'text-ok' : 'text-text-tertiary'}`}>
                {coherence.cadence.should_run ? 'yes' : 'no'}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-xs text-text-tertiary">Cadence not available</p>
        )}
      </section>

      {/* ── Phase 9.8: Merge Verifications ── */}
      {coherence.mergeVerifications && coherence.mergeVerifications.count > 0 && (
        <section>
          <h3 className="wv-label mb-3">
            Merge Verifications
            <span className="ml-2 font-mono text-xs text-cyan">{coherence.mergeVerifications.count}</span>
          </h3>
          <div className="space-y-1.5">
            {coherence.mergeVerifications.verifications.slice(-5).reverse().map((mv: Record<string, unknown>) => (
              <div key={mv.verification_id as string} className="wv-card p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`font-mono text-xs px-1.5 py-0.5 rounded uppercase ${
                    mv.status === 'production_verified' || mv.status === 'cleanup_ready' ? 'bg-ok/20 text-ok' :
                    mv.status === 'validation_failed' || mv.status === 'production_rejected' ? 'bg-danger/20 text-danger' :
                    'bg-surface-overlay text-text-secondary'
                  }`}>{mv.status as string}</span>
                  <span className="font-mono text-xs text-text-tertiary">{mv.verification_id as string}</span>
                </div>
                {(mv.pr_number as number) > 0 && (
                  <p className="text-xs font-mono text-ok">PR #{mv.pr_number as number}</p>
                )}
                {mv.merge_commit && (
                  <p className="text-xs font-mono text-text-tertiary">merge: {(mv.merge_commit as string).slice(0, 12)}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Phase 9.4: Coherence Propagation ── */}

      {/* Template Registry */}
      <section>
        <h3 className="wv-label mb-3">
          Template Registry
          {coherence.templates?.summary && (
            <span className="ml-2 font-mono text-xs text-cyan">
              {coherence.templates.summary.promoted_count} promoted / {coherence.templates.summary.total_candidates} total
            </span>
          )}
        </h3>
        {coherence.templates?.candidates && coherence.templates.candidates.length > 0 ? (
          <div className="space-y-1.5">
            {coherence.templates.candidates.slice(0, 8).map((tpl) => (
              <div key={tpl.template_id} className="wv-card p-3 flex items-center gap-3">
                <TemplateStatusBadge status={tpl.status} />
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-mono">{tpl.template_type.replace(/_/g, ' ')}</span>
                </div>
                <ConfidenceDot value={tpl.confidence} />
                <span className="font-mono text-xs text-text-tertiary">{(tpl.confidence * 100).toFixed(0)}%</span>
                <span className="font-mono text-xs text-text-tertiary">
                  {tpl.observed_success_count}✓ {tpl.observed_failure_count}✗
                </span>
                {(tpl.status === 'raw' || tpl.status === 'candidate') && (
                  <button
                    onClick={() => coherence.approveTemplate(tpl.template_id)}
                    className="text-xs text-ok hover:underline font-mono"
                  >
                    approve
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-tertiary">No template candidates yet</p>
        )}
        {coherence.templates?.promoted && coherence.templates.promoted.length > 0 && (
          <div className="mt-2">
            <p className="text-xs text-text-tertiary mb-1">Promoted:</p>
            {coherence.templates.promoted.map((tpl) => (
              <div key={tpl.template_id} className="flex items-center gap-2 py-0.5">
                <TemplateStatusBadge status="promoted" />
                <span className="text-xs font-mono">{tpl.template_type.replace(/_/g, ' ')}</span>
                <span className="text-xs text-ok font-mono">{(tpl.confidence * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Agent Capabilities */}
      <section>
        <h3 className="wv-label mb-3">
          Agent Capabilities
          {coherence.agentCapabilities?.summary && (
            <span className="ml-2 font-mono text-xs text-text-tertiary">
              {coherence.agentCapabilities.summary.total_profiles} profiles / {coherence.agentCapabilities.summary.total_records} records
            </span>
          )}
        </h3>
        {coherence.agentCapabilities?.profiles && Object.keys(coherence.agentCapabilities.profiles).length > 0 ? (
          <div className="space-y-2">
            {Object.entries(coherence.agentCapabilities.profiles).map(([agentType, profile]) => (
              <div key={agentType} className="wv-card p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-mono">{agentType.replace(/_/g, ' ')}</span>
                  <span className={`font-mono text-xs ${profile.overall_reliability >= 0.8 ? 'text-ok' : profile.overall_reliability >= 0.5 ? 'text-warn' : 'text-danger'}`}>
                    {(profile.overall_reliability * 100).toFixed(0)}% reliable
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-1">
                  {Object.entries(profile.capabilities).map(([capName, cap]) => (
                    <div key={capName} className="flex items-center gap-1">
                      <ConfidenceDot value={cap.confidence} />
                      <span className="text-xs font-mono text-text-secondary truncate">{capName.replace(/_/g, ' ')}</span>
                      <span className="text-xs font-mono text-text-tertiary ml-auto">{cap.successes}/{cap.attempts}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-tertiary">No agent capability data yet</p>
        )}
      </section>

      {/* Spine-Native Propagation Status */}
      <section>
        <h3 className="wv-label mb-3">
          Spine-Native Propagation
          {coherence.propagation?.spine_native ? (
            <span className="ml-2 font-mono text-xs text-ok">ACTIVE</span>
          ) : (
            <span className="ml-2 font-mono text-xs text-warn">NOT WIRED</span>
          )}
        </h3>
        <div className="wv-card p-3 space-y-1">
          <div className="flex items-center gap-3">
            <span className="wv-label w-40">Automatic propagation</span>
            <span className={`font-mono text-xs ${coherence.propagation?.spine_native ? 'text-ok' : 'text-danger'}`}>
              {coherence.propagation?.spine_native ? 'Yes — spine emits OutcomeCommitted automatically' : 'No — requires manual calls'}
            </span>
          </div>
          {coherence.propagation?.summary && (
            <>
              <div className="flex items-center gap-3">
                <span className="wv-label w-40">Targets registered</span>
                <span className="font-mono text-xs">{coherence.propagation.summary.registered_targets}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="wv-label w-40">Processed outcomes</span>
                <span className="font-mono text-xs">{coherence.propagation.processed_outcome_count ?? 0}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="wv-label w-40">Total propagations</span>
                <span className="font-mono text-xs">{coherence.propagation.summary.total_events}</span>
              </div>
            </>
          )}
        </div>
      </section>

      {/* Propagation Events */}
      <section>
        <h3 className="wv-label mb-3">
          Coherence Propagation
          {coherence.propagation?.summary && (
            <span className="ml-2 font-mono text-xs text-text-tertiary">
              {coherence.propagation.summary.total_events} events / {coherence.propagation.summary.total_succeeded} ok / {coherence.propagation.summary.total_failed} failed
            </span>
          )}
        </h3>
        {coherence.propagation?.recent_events && coherence.propagation.recent_events.length > 0 ? (
          <div className="space-y-1.5">
            {coherence.propagation.recent_events.slice(0, 5).map((ev) => (
              <div key={ev.event_id} className="wv-card p-3 flex items-center gap-3">
                <PropagationStatusDot status={ev.status} />
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-mono">{ev.event_id}</span>
                </div>
                <span className="font-mono text-xs text-ok">{ev.succeeded_targets}✓</span>
                {ev.failed_targets > 0 && (
                  <span className="font-mono text-xs text-danger">{ev.failed_targets}✗</span>
                )}
                <span className="font-mono text-xs text-text-tertiary">{ev.total_targets} targets</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-tertiary">No propagation events yet</p>
        )}
        {coherence.propagation?.registered_targets && coherence.propagation.registered_targets.length > 0 && (
          <div className="mt-2">
            <p className="text-xs text-text-tertiary mb-1">Registered targets ({coherence.propagation.registered_targets.length}):</p>
            <div className="flex flex-wrap gap-1">
              {coherence.propagation.registered_targets.map((t) => (
                <span key={t.name} className="text-xs font-mono bg-surface-overlay px-1.5 py-0.5 rounded">
                  W{t.wave}:{t.name}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
