import { useState } from 'react'
import { useWorldModelStore } from '../stores/worldModelStore'
import { usePolling } from '../hooks/usePolling'

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-danger',
  high: 'text-warn',
  medium: 'text-cyan',
  low: 'text-text-secondary',
  info: 'text-text-tertiary',
}

const STATUS_COLORS: Record<string, string> = {
  operational: 'text-ok',
  degraded: 'text-warn',
  partial: 'text-cyan',
  dormant: 'text-text-tertiary',
  missing: 'text-danger',
  unknown: 'text-text-tertiary',
}

const RISK_BADGE: Record<string, string> = {
  low: 'bg-ok/20 text-ok',
  medium: 'bg-warn/20 text-warn',
  high: 'bg-danger/20 text-danger',
  critical: 'bg-danger/30 text-danger',
}

const TABS = [
  { id: 'world' as const, label: 'World' },
  { id: 'graph' as const, label: 'Dependencies' },
  { id: 'contradictions' as const, label: 'Contradictions' },
  { id: 'compose' as const, label: 'Compose' },
  { id: 'outcomes' as const, label: 'Outcomes' },
  { id: 'memory' as const, label: 'Memory' },
]

function TabBar() {
  const tab = useWorldModelStore((s) => s.tab)
  const setTab = useWorldModelStore((s) => s.setTab)
  const contradictions = useWorldModelStore((s) => s.contradictions)
  const memoryPromotion = useWorldModelStore((s) => s.memoryPromotion)

  return (
    <div className="flex items-center gap-1 px-4 py-2 border-b border-border bg-canvas">
      {TABS.map((t) => (
        <button
          key={t.id}
          onClick={() => setTab(t.id)}
          className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
            tab === t.id
              ? 'bg-cyan/20 text-cyan'
              : 'text-text-secondary hover:text-text-primary hover:bg-surface-overlay'
          }`}
        >
          {t.label}
          {t.id === 'contradictions' && contradictions && contradictions.summary.total > 0 && (
            <span className="ml-1.5 text-warn">{contradictions.summary.total}</span>
          )}
          {t.id === 'memory' && memoryPromotion && memoryPromotion.summary.pending_approvals > 0 && (
            <span className="ml-1.5 text-cyan">{memoryPromotion.summary.pending_approvals}</span>
          )}
        </button>
      ))}
    </div>
  )
}

function WorldTab() {
  const worldModel = useWorldModelStore((s) => s.worldModel)

  if (!worldModel) return <Empty msg="Loading world model..." />

  const entities = Object.values(worldModel.entities)
  const byCategory: Record<string, typeof entities> = {}
  for (const e of entities) {
    if (!byCategory[e.category]) byCategory[e.category] = []
    byCategory[e.category].push(e)
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Entities" value={worldModel.summary.total_entities} />
        <Stat label="Gaps" value={worldModel.summary.total_gaps} color={worldModel.summary.total_gaps > 0 ? 'warn' : 'ok'} />
        <Stat label="Uncertainties" value={worldModel.summary.total_uncertainties} />
        <Stat label="Extracted" value={new Date(worldModel.extracted_at * 1000).toLocaleTimeString()} />
      </div>

      <div className="grid grid-cols-3 gap-2">
        {Object.entries(worldModel.summary.by_status).map(([status, count]) => (
          <div key={status} className="flex items-center gap-2">
            <span className={`text-xs font-mono ${STATUS_COLORS[status] || 'text-text-tertiary'}`}>{status}</span>
            <span className="text-xs font-mono text-text-primary">{count}</span>
          </div>
        ))}
      </div>

      {Object.entries(byCategory).sort().map(([cat, ents]) => (
        <section key={cat}>
          <h3 className="wv-label mb-2">{cat.replace(/_/g, ' ')} ({ents.length})</h3>
          <div className="space-y-1">
            {ents.sort((a, b) => a.name.localeCompare(b.name)).map((e) => (
              <div key={e.id} className="flex items-center gap-2 py-0.5 px-2 rounded hover:bg-surface-overlay">
                <span className={`w-1.5 h-1.5 rounded-full ${statusDot(e.status)}`} />
                <span className="text-xs text-text-primary flex-1 truncate">{e.name}</span>
                <span className={`text-[10px] font-mono ${STATUS_COLORS[e.status] || 'text-text-tertiary'}`}>{e.status}</span>
                {e.evidence.length > 0 && (
                  <span className="text-[10px] text-text-tertiary">{e.evidence.length} ev</span>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}

      {worldModel.gaps.length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Gaps ({worldModel.gaps.length})</h3>
          <div className="space-y-1">
            {worldModel.gaps.map((g) => (
              <div key={g.id} className="wv-card p-2">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-mono uppercase ${SEVERITY_COLORS[g.severity]}`}>{g.severity}</span>
                  <span className="text-xs text-text-primary flex-1">{g.description}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {worldModel.uncertainties.length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Uncertainties ({worldModel.uncertainties.length})</h3>
          <div className="space-y-1">
            {worldModel.uncertainties.map((u) => (
              <div key={u.id} className="flex items-center gap-2 py-0.5">
                <span className="text-[10px] font-mono text-text-tertiary">{(u.confidence * 100).toFixed(0)}%</span>
                <span className="text-xs text-text-secondary flex-1">{u.description}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function GraphTab() {
  const depGraph = useWorldModelStore((s) => s.depGraph)

  if (!depGraph) return <Empty msg="Loading dependency graph..." />

  const { summary, orphaned, cycles, critical_paths, edges } = depGraph

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Nodes" value={summary.total_nodes} />
        <Stat label="Edges" value={summary.total_edges} />
        <Stat label="Orphans" value={summary.orphaned} color={summary.orphaned > 0 ? 'warn' : 'ok'} />
        <Stat label="Cycles" value={summary.cycles} color={summary.cycles > 0 ? 'danger' : 'ok'} />
      </div>

      {summary.critical_path_length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Critical Paths</h3>
          <div className="space-y-2">
            {critical_paths.map((cp, i) => (
              <div key={i} className="wv-card p-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-[10px] font-mono uppercase ${SEVERITY_COLORS[cp.risk]}`}>{cp.risk}</span>
                  <span className="text-[10px] text-text-tertiary">length {cp.length}</span>
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  {cp.path.map((node, idx) => (
                    <span key={idx} className="text-xs font-mono text-text-primary">
                      {node}{idx < cp.path.length - 1 && <span className="text-text-tertiary mx-0.5">&rarr;</span>}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {cycles.length > 0 && (
        <section>
          <h3 className="wv-label mb-2 text-danger">Circular Dependencies</h3>
          <div className="space-y-1">
            {cycles.map((cycle, i) => (
              <div key={i} className="text-xs font-mono text-danger/80">{cycle.join(' → ')}</div>
            ))}
          </div>
        </section>
      )}

      {orphaned.length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Orphaned Nodes ({orphaned.length})</h3>
          <div className="flex flex-wrap gap-1">
            {orphaned.map((id) => (
              <span key={id} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-overlay text-text-tertiary">{id}</span>
            ))}
          </div>
        </section>
      )}

      <section>
        <h3 className="wv-label mb-2">Edge Types</h3>
        <div className="grid grid-cols-3 gap-2">
          {Object.entries(summary.edge_types).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
            <div key={type} className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">{type}</span>
              <span className="text-xs font-mono text-text-primary">{count}</span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3 className="wv-label mb-2">All Edges ({edges.length})</h3>
        <div className="max-h-60 overflow-y-auto space-y-0.5">
          {edges.map((e, i) => (
            <div key={i} className="flex items-center gap-2 py-0.5 text-[11px] font-mono">
              <span className="text-text-primary">{e.source}</span>
              <span className="text-text-tertiary">&rarr;</span>
              <span className="text-text-primary">{e.target}</span>
              <span className="text-text-tertiary ml-auto">{e.type}</span>
              <span className={`text-[9px] ${e.strength === 'hard' ? 'text-cyan' : 'text-text-tertiary'}`}>{e.strength}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function ContradictionsTab() {
  const contradictions = useWorldModelStore((s) => s.contradictions)
  const compose = useWorldModelStore((s) => s.compose)
  const composing = useWorldModelStore((s) => s.composing)

  if (!contradictions) return <Empty msg="Loading contradictions..." />

  const topContradiction = contradictions.contradictions[0]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Total" value={contradictions.summary.total} color={contradictions.summary.total > 0 ? 'warn' : 'ok'} />
        <Stat label="Critical" value={contradictions.summary.by_severity?.critical ?? 0} color={(contradictions.summary.by_severity?.critical ?? 0) > 0 ? 'danger' : 'ok'} />
        <Stat label="High" value={contradictions.summary.by_severity?.high ?? 0} color={(contradictions.summary.by_severity?.high ?? 0) > 0 ? 'warn' : 'ok'} />
        <Stat label="Checks" value={contradictions.summary.checks_performed} />
      </div>

      {topContradiction && (
        <div className="wv-card p-3 border border-warn/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-warn font-mono uppercase">Top Contradiction</span>
            <button
              onClick={() => compose(`Fix: ${topContradiction.recommended_fix || topContradiction.type}`)}
              disabled={composing}
              className="px-2 py-0.5 text-[10px] font-mono bg-cyan/20 text-cyan rounded hover:bg-cyan/30 disabled:opacity-50"
            >
              {composing ? 'COMPOSING...' : 'COMPOSE FIX'}
            </button>
          </div>
          <p className="text-xs text-text-primary">{topContradiction.type.replace(/_/g, ' ')}</p>
          {topContradiction.recommended_fix && (
            <p className="text-xs text-text-secondary mt-1">{topContradiction.recommended_fix}</p>
          )}
          <div className="flex items-center gap-3 mt-1.5">
            <span className={`text-[10px] font-mono ${SEVERITY_COLORS[topContradiction.severity]}`}>{topContradiction.severity}</span>
            <span className="text-[10px] text-text-tertiary">{(topContradiction.confidence * 100).toFixed(0)}% confidence</span>
          </div>
        </div>
      )}

      <section>
        <h3 className="wv-label mb-2">All Contradictions</h3>
        <div className="space-y-1.5">
          {contradictions.contradictions.map((c) => (
            <div key={c.id} className="wv-card p-2">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-mono uppercase ${SEVERITY_COLORS[c.severity]}`}>{c.severity}</span>
                <span className="text-xs text-text-primary flex-1">{c.type.replace(/_/g, ' ')}</span>
                <span className="text-[10px] text-text-tertiary">{(c.confidence * 100).toFixed(0)}%</span>
              </div>
              {c.recommended_fix && (
                <p className="text-[10px] text-text-secondary mt-1 ml-12">{c.recommended_fix}</p>
              )}
            </div>
          ))}
          {contradictions.contradictions.length === 0 && (
            <p className="text-xs text-ok font-mono">No contradictions detected</p>
          )}
        </div>
      </section>
    </div>
  )
}

function ComposeTab() {
  const plan = useWorldModelStore((s) => s.plan)
  const compose = useWorldModelStore((s) => s.compose)
  const composing = useWorldModelStore((s) => s.composing)
  const [intent, setIntent] = useState('')

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && intent.trim()) compose(intent.trim()) }}
          placeholder="Describe what to fix or improve..."
          className="flex-1 px-3 py-1.5 text-xs font-mono bg-surface border border-border rounded text-text-primary placeholder-text-tertiary focus:border-cyan focus:outline-none"
        />
        <button
          onClick={() => intent.trim() && compose(intent.trim())}
          disabled={composing || !intent.trim()}
          className="px-3 py-1.5 text-xs font-mono bg-cyan/20 text-cyan rounded hover:bg-cyan/30 disabled:opacity-50"
        >
          {composing ? 'COMPOSING...' : 'COMPOSE'}
        </button>
      </div>

      {plan && (
        <div className="space-y-3">
          <div className="wv-card p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-text-primary">{plan.summary.intent}</span>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${RISK_BADGE[plan.overall_risk]}`}>{plan.overall_risk}</span>
                <span className="text-[10px] font-mono text-text-tertiary">{plan.governance_required}</span>
              </div>
            </div>
            <div className="grid grid-cols-4 gap-2 text-[10px] text-text-tertiary">
              <span>{plan.summary.total_steps} steps</span>
              <span>{plan.summary.risks} risks</span>
              <span>{plan.summary.missing_prerequisites} missing</span>
              <span>ID: {plan.summary.plan_id}</span>
            </div>
          </div>

          <section>
            <h3 className="wv-label mb-2">Steps</h3>
            <div className="space-y-1.5">
              {plan.steps.map((step, idx) => (
                <div key={step.id} className="wv-card p-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-text-tertiary w-4">{idx + 1}</span>
                    <span className={`text-[10px] font-mono px-1 rounded ${RISK_BADGE[step.risk_class]}`}>{step.risk_class}</span>
                    <span className="text-xs text-text-primary flex-1">{step.description}</span>
                    <span className="text-[10px] font-mono text-text-tertiary">{step.governance_mode}</span>
                  </div>
                  {step.verification && (
                    <p className="text-[10px] text-text-secondary mt-0.5 ml-6">verify: {step.verification}</p>
                  )}
                </div>
              ))}
            </div>
          </section>

          {plan.risks.length > 0 && (
            <section>
              <h3 className="wv-label mb-2">Risks</h3>
              <div className="space-y-1">
                {plan.risks.map((r, i) => (
                  <div key={i} className="flex items-start gap-2 py-0.5">
                    <span className={`text-[10px] font-mono ${SEVERITY_COLORS[r.risk_class]}`}>{r.risk_class}</span>
                    <div className="flex-1">
                      <p className="text-xs text-text-primary">{r.description}</p>
                      {r.mitigation && <p className="text-[10px] text-text-secondary">{r.mitigation}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {plan.evidence.length > 0 && (
            <section>
              <h3 className="wv-label mb-2">Evidence</h3>
              <div className="space-y-0.5">
                {plan.evidence.map((ev, i) => (
                  <p key={i} className="text-[10px] font-mono text-text-tertiary">{ev}</p>
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {!plan && !composing && (
        <div className="text-center py-8">
          <p className="text-xs text-text-tertiary">Compose a plan from observed capabilities.</p>
          <p className="text-[10px] text-text-tertiary mt-1">Intent → Capabilities → Dependencies → Risks → Executable plan</p>
        </div>
      )}
    </div>
  )
}

function OutcomesTab() {
  const learningLoop = useWorldModelStore((s) => s.learningLoop)

  if (!learningLoop) return <Empty msg="Loading outcome history..." />

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Outcomes" value={learningLoop.total_outcomes} />
        <Stat label="Success" value={learningLoop.by_status?.success ?? 0} color="ok" />
        <Stat label="Failed" value={learningLoop.by_status?.failure ?? 0} color={(learningLoop.by_status?.failure ?? 0) > 0 ? 'danger' : 'ok'} />
        <Stat label="Signals" value={learningLoop.signals?.length ?? 0} />
      </div>

      {learningLoop.signals && learningLoop.signals.length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Learning Signals</h3>
          <div className="space-y-1">
            {learningLoop.signals.map((s, i) => (
              <div key={i} className="wv-card p-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-cyan">{s.signal_type.replace(/_/g, ' ')}</span>
                  <span className="text-xs text-text-primary flex-1">{s.description}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {Object.keys(learningLoop.reliability ?? {}).length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Reliability by Action</h3>
          <div className="space-y-1">
            {Object.entries(learningLoop.reliability).sort((a, b) => a[1] - b[1]).map(([action, rate]) => (
              <div key={action} className="flex items-center gap-2">
                <span className="text-xs text-text-primary flex-1">{action.replace(/_/g, ' ')}</span>
                <div className="w-24 h-1.5 bg-surface-overlay rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${rate >= 0.8 ? 'bg-ok' : rate >= 0.5 ? 'bg-warn' : 'bg-danger'}`} style={{ width: `${rate * 100}%` }} />
                </div>
                <span className="text-[10px] font-mono w-8 text-right">{(rate * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {learningLoop.recent_outcomes && learningLoop.recent_outcomes.length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Recent Outcomes</h3>
          <div className="space-y-1">
            {learningLoop.recent_outcomes.map((o) => (
              <div key={o.id} className="flex items-center gap-2 py-0.5">
                <span className={`w-1.5 h-1.5 rounded-full ${o.status === 'success' ? 'bg-ok' : o.status === 'failure' ? 'bg-danger' : 'bg-warn'}`} />
                <span className="text-xs text-text-primary flex-1 truncate">{o.description || o.action_type}</span>
                <span className="text-[10px] font-mono text-text-tertiary">{o.duration_seconds.toFixed(1)}s</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {learningLoop.promotion_candidates && learningLoop.promotion_candidates.length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Promotion Candidates</h3>
          <div className="flex flex-wrap gap-1">
            {learningLoop.promotion_candidates.map((id) => (
              <span key={id} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan/10 text-cyan">{id}</span>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function MemoryTab() {
  const memoryPromotion = useWorldModelStore((s) => s.memoryPromotion)
  const approveMemory = useWorldModelStore((s) => s.approveMemory)
  const rejectMemory = useWorldModelStore((s) => s.rejectMemory)

  if (!memoryPromotion) return <Empty msg="Loading memory promotion..." />

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Candidates" value={memoryPromotion.summary.total_candidates} />
        <Stat label="Canonical" value={memoryPromotion.summary.canonical_entries} color="ok" />
        <Stat label="Pending" value={memoryPromotion.summary.pending_approvals} color={memoryPromotion.summary.pending_approvals > 0 ? 'cyan' : 'ok'} />
        <Stat label="Status" value={Object.keys(memoryPromotion.summary.by_status).length + ' states'} />
      </div>

      {memoryPromotion.pending_approvals.length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Pending Approvals</h3>
          <div className="space-y-2">
            {memoryPromotion.pending_approvals.map((c) => (
              <div key={c.id} className="wv-card p-3">
                <p className="text-xs text-text-primary mb-1.5">{c.content}</p>
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-[10px] font-mono text-text-tertiary">{c.category}</span>
                  <span className="text-[10px] font-mono text-text-tertiary">{c.scope}</span>
                  <span className="text-[10px] font-mono text-text-tertiary">{(c.confidence * 100).toFixed(0)}% conf</span>
                  {c.source_action && <span className="text-[10px] font-mono text-text-tertiary">from: {c.source_action}</span>}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => approveMemory(c.id)}
                    className="px-2 py-0.5 text-[10px] font-mono bg-ok/20 text-ok rounded hover:bg-ok/30"
                  >
                    PROMOTE
                  </button>
                  <button
                    onClick={() => rejectMemory(c.id, 'operator_rejected')}
                    className="px-2 py-0.5 text-[10px] font-mono bg-danger/20 text-danger rounded hover:bg-danger/30"
                  >
                    REJECT
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {memoryPromotion.pending_approvals.length === 0 && (
        <div className="text-center py-8">
          <p className="text-xs text-ok font-mono">No pending promotions</p>
          <p className="text-[10px] text-text-tertiary mt-1">Patterns detected through repeated outcomes will surface here.</p>
        </div>
      )}

      {Object.keys(memoryPromotion.summary.by_status).length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Pipeline Status</h3>
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(memoryPromotion.summary.by_status).map(([status, count]) => (
              <div key={status} className="flex items-center gap-2">
                <span className="text-xs text-text-secondary">{status}</span>
                <span className="text-xs font-mono text-text-primary">{count}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export function WorldModelPanel() {
  const tab = useWorldModelStore((s) => s.tab)
  const fetchAll = useWorldModelStore((s) => s.fetchAll)

  usePolling(fetchAll, 20000)

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TabBar />
      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'world' && <WorldTab />}
        {tab === 'graph' && <GraphTab />}
        {tab === 'contradictions' && <ContradictionsTab />}
        {tab === 'compose' && <ComposeTab />}
        {tab === 'outcomes' && <OutcomesTab />}
        {tab === 'memory' && <MemoryTab />}
      </div>
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: string | number; color?: string }) {
  const colorClass = color === 'ok' ? 'text-ok' : color === 'warn' ? 'text-warn' : color === 'danger' ? 'text-danger' : color === 'cyan' ? 'text-cyan' : 'text-text-primary'
  return (
    <div className="wv-card px-2 py-1.5 text-center">
      <div className="text-[8px] text-text-tertiary uppercase">{label}</div>
      <div className={`text-xs font-mono font-semibold ${colorClass}`}>{value}</div>
    </div>
  )
}

function Empty({ msg }: { msg: string }) {
  return (
    <div className="h-full flex items-center justify-center">
      <p className="text-text-tertiary text-sm">{msg}</p>
    </div>
  )
}

function statusDot(status: string): string {
  if (status === 'operational') return 'bg-ok'
  if (status === 'degraded') return 'bg-warn'
  if (status === 'partial') return 'bg-cyan'
  if (status === 'missing') return 'bg-danger'
  return 'bg-text-tertiary'
}
