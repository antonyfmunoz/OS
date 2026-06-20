import { useEffect, useState } from 'react'
import { useEngineeringStore } from '../stores/engineeringStore'

const RISK_COLORS: Record<string, string> = {
  low: '#22c55e',
  medium: '#f59e0b',
  high: '#ef4444',
  critical: '#dc2626',
}

const STATUS_COLORS: Record<string, string> = {
  draft: '#6b7280',
  approved: '#22c55e',
  rejected: '#ef4444',
  executing: '#3b82f6',
  completed: '#10b981',
  failed: '#dc2626',
}

const GAP_COLORS: Record<string, string> = {
  blocked: '#ef4444',
  stale: '#f59e0b',
  missing_validation: '#3b82f6',
  not_started: '#6b7280',
}

const RECOMMENDATION_COLORS: Record<string, string> = {
  approve: '#22c55e',
  approve_with_notes: '#f59e0b',
  needs_review: '#3b82f6',
  reject: '#ef4444',
}

function TabBar({ active, onSelect }: { active: string; onSelect: (t: string) => void }) {
  const tabs = ['intent', 'plan', 'queue', 'sessions', 'review', 'gaps'] as const
  return (
    <div style={{ display: 'flex', gap: 2, marginBottom: 16, borderBottom: '1px solid #333' }}>
      {tabs.map((t) => (
        <button
          key={t}
          onClick={() => onSelect(t)}
          style={{
            padding: '8px 16px',
            background: active === t ? '#1e293b' : 'transparent',
            color: active === t ? '#fff' : '#9ca3af',
            border: 'none',
            borderBottom: active === t ? '2px solid #3b82f6' : '2px solid transparent',
            cursor: 'pointer',
            textTransform: 'capitalize',
            fontSize: 13,
          }}
        >
          {t}
        </button>
      ))}
    </div>
  )
}

function IntentTab() {
  const [intent, setIntent] = useState('')
  const { createPlan, loading } = useEngineeringStore()

  return (
    <div style={{ padding: 16 }}>
      <h3 style={{ margin: '0 0 12px', fontSize: 15, color: '#e2e8f0' }}>Engineering Intent</h3>
      <p style={{ color: '#9ca3af', fontSize: 12, marginBottom: 12 }}>
        Describe what you want to build. The planner will decompose it into tasks, assess risk, and produce a reviewable plan.
      </p>
      <textarea
        value={intent}
        onChange={(e) => setIntent(e.target.value)}
        placeholder="e.g. Add a health endpoint to the API"
        style={{
          width: '100%',
          minHeight: 80,
          padding: 10,
          background: '#0f172a',
          color: '#e2e8f0',
          border: '1px solid #334155',
          borderRadius: 6,
          fontSize: 13,
          resize: 'vertical',
        }}
      />
      <button
        onClick={() => { if (intent.trim()) createPlan(intent.trim()) }}
        disabled={loading || !intent.trim()}
        style={{
          marginTop: 10,
          padding: '8px 20px',
          background: loading ? '#374151' : '#3b82f6',
          color: '#fff',
          border: 'none',
          borderRadius: 6,
          cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: 13,
        }}
      >
        {loading ? 'Creating Plan...' : 'Create Plan'}
      </button>
    </div>
  )
}

function PlanTab() {
  const { activePlan, approvePlan, rejectPlan, loading, lastReceipt } = useEngineeringStore()

  if (!activePlan) {
    return (
      <div style={{ padding: 16, color: '#9ca3af' }}>
        No plan selected. Create one from the Intent tab.
      </div>
    )
  }

  const p = activePlan
  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: 15, color: '#e2e8f0' }}>Engineering Plan</h3>
        <span style={{ color: STATUS_COLORS[p.status] || '#6b7280', fontSize: 12, textTransform: 'uppercase' }}>
          {p.status}
        </span>
      </div>

      <div style={{ background: '#0f172a', padding: 12, borderRadius: 6, marginBottom: 12, border: '1px solid #1e293b' }}>
        <div style={{ fontSize: 12, color: '#9ca3af' }}>Goal</div>
        <div style={{ color: '#e2e8f0', fontSize: 13 }}>{p.intent.goal}</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
        <div style={{ background: '#0f172a', padding: 10, borderRadius: 6, border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>Type</div>
          <div style={{ color: '#e2e8f0', fontSize: 13 }}>{p.intent.intent_type}</div>
        </div>
        <div style={{ background: '#0f172a', padding: 10, borderRadius: 6, border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>Risk</div>
          <div style={{ color: RISK_COLORS[p.estimated_total_risk] || '#9ca3af', fontSize: 13 }}>{p.estimated_total_risk}</div>
        </div>
      </div>

      {p.intent.scope.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 4 }}>Scope</div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {p.intent.scope.map((s) => (
              <span key={s} style={{ background: '#1e293b', padding: '2px 8px', borderRadius: 4, fontSize: 11, color: '#94a3b8' }}>{s}</span>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 8 }}>Tasks ({p.tasks.length})</div>
        {p.tasks.map((task, i) => (
          <div key={task.task_id} style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 6 }}>
            <div style={{ minWidth: 24, color: '#6b7280', fontSize: 12, marginTop: 2 }}>{i + 1}.</div>
            <div style={{ flex: 1 }}>
              <div style={{ color: '#e2e8f0', fontSize: 13 }}>{task.title}</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
                <span style={{ fontSize: 11, color: '#6b7280' }}>{task.task_type}</span>
                <span style={{ fontSize: 11, color: RISK_COLORS[task.risk_class] || '#6b7280' }}>{task.risk_class}</span>
              </div>
            </div>
            {i < p.tasks.length - 1 && (
              <div style={{ color: '#374151', marginLeft: 8, fontSize: 12 }}>→</div>
            )}
          </div>
        ))}
      </div>

      {p.status === 'draft' && (
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => approvePlan(p.plan_id)}
            disabled={loading}
            style={{
              padding: '8px 20px',
              background: '#22c55e',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            Approve & Generate Packets
          </button>
          <button
            onClick={() => rejectPlan(p.plan_id)}
            disabled={loading}
            style={{
              padding: '8px 20px',
              background: '#ef4444',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            Reject
          </button>
        </div>
      )}

      {lastReceipt && lastReceipt.plan_id === p.plan_id && (
        <div style={{ marginTop: 12, background: '#0f172a', padding: 12, borderRadius: 6, border: '1px solid #22c55e44' }}>
          <div style={{ fontSize: 12, color: '#22c55e', marginBottom: 4 }}>Packets Generated</div>
          <div style={{ color: '#9ca3af', fontSize: 12 }}>
            {lastReceipt.work_packet_ids.length} work packets created
          </div>
        </div>
      )}
    </div>
  )
}

function QueueTab() {
  const { queueSummary, fetchQueue, loading } = useEngineeringStore()

  useEffect(() => { fetchQueue() }, [])

  if (loading) return <div style={{ padding: 16, color: '#9ca3af' }}>—</div>

  const summary = queueSummary as Record<string, unknown> | null
  if (!summary) return <div style={{ padding: 16, color: '#9ca3af' }}>No engineering packets in queue.</div>

  const total = (summary.total_engineering_packets as number) || 0
  const byStatus = (summary.by_status as Record<string, number>) || {}
  const packets = (summary.packets as Array<Record<string, unknown>>) || []

  return (
    <div style={{ padding: 16 }}>
      <h3 style={{ margin: '0 0 12px', fontSize: 15, color: '#e2e8f0' }}>Engineering Queue</h3>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <div style={{ background: '#0f172a', padding: 10, borderRadius: 6, border: '1px solid #1e293b', minWidth: 80 }}>
          <div style={{ fontSize: 20, color: '#e2e8f0' }}>{total}</div>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>Total</div>
        </div>
        {Object.entries(byStatus).map(([status, count]) => (
          <div key={status} style={{ background: '#0f172a', padding: 10, borderRadius: 6, border: '1px solid #1e293b', minWidth: 80 }}>
            <div style={{ fontSize: 20, color: STATUS_COLORS[status] || '#e2e8f0' }}>{count}</div>
            <div style={{ fontSize: 11, color: '#9ca3af' }}>{status}</div>
          </div>
        ))}
      </div>
      {packets.slice(0, 20).map((pkt) => (
        <div key={pkt.packet_id as string} style={{ background: '#0f172a', padding: 10, borderRadius: 6, border: '1px solid #1e293b', marginBottom: 6 }}>
          <div style={{ color: '#e2e8f0', fontSize: 13 }}>{pkt.title as string}</div>
          <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>
            {pkt.status as string} · {pkt.domain as string} · {pkt.risk_class as string}
          </div>
        </div>
      ))}
    </div>
  )
}

function GapsTab() {
  const { gapAnalysis, gapRecommendations, fetchGaps, loading, createPlan } = useEngineeringStore()

  useEffect(() => { fetchGaps() }, [])

  if (loading) return <div style={{ padding: 16, color: '#9ca3af' }}>—</div>

  return (
    <div style={{ padding: 16 }}>
      <h3 style={{ margin: '0 0 12px', fontSize: 15, color: '#e2e8f0' }}>Roadmap Gaps</h3>

      {gapAnalysis && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <div style={{ background: '#0f172a', padding: 10, borderRadius: 6, border: '1px solid #1e293b', minWidth: 80 }}>
            <div style={{ fontSize: 20, color: '#e2e8f0' }}>{gapAnalysis.completion_percentage}%</div>
            <div style={{ fontSize: 11, color: '#9ca3af' }}>Complete</div>
          </div>
          <div style={{ background: '#0f172a', padding: 10, borderRadius: 6, border: '1px solid #1e293b', minWidth: 80 }}>
            <div style={{ fontSize: 20, color: '#e2e8f0' }}>{gapAnalysis.gaps.length}</div>
            <div style={{ fontSize: 11, color: '#9ca3af' }}>Gaps</div>
          </div>
          <div style={{ background: '#0f172a', padding: 10, borderRadius: 6, border: '1px solid #1e293b', minWidth: 80 }}>
            <div style={{ fontSize: 20, color: '#ef4444' }}>{gapAnalysis.blocked_phases}</div>
            <div style={{ fontSize: 11, color: '#9ca3af' }}>Blocked</div>
          </div>
        </div>
      )}

      {gapRecommendations.length > 0 && (
        <div>
          <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 8 }}>Recommended Work</div>
          {gapRecommendations.map((rec) => (
            <div key={rec.recommendation_id} style={{ background: '#0f172a', padding: 12, borderRadius: 6, border: '1px solid #1e293b', marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ color: '#e2e8f0', fontSize: 13 }}>{rec.title}</div>
                <span style={{ fontSize: 11, color: RISK_COLORS[rec.estimated_risk] || '#6b7280' }}>{rec.estimated_risk}</span>
              </div>
              <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>{rec.description}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                <span style={{ fontSize: 11, color: '#6b7280' }}>Priority: {(rec.priority_score * 100).toFixed(0)}%</span>
                <button
                  onClick={() => createPlan(rec.intent_text)}
                  style={{
                    padding: '4px 12px',
                    background: '#1e293b',
                    color: '#3b82f6',
                    border: '1px solid #334155',
                    borderRadius: 4,
                    cursor: 'pointer',
                    fontSize: 11,
                  }}
                >
                  Plan This
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {!gapAnalysis && !loading && (
        <div style={{ color: '#9ca3af', fontSize: 13 }}>No roadmap data available.</div>
      )}
    </div>
  )
}

function SessionsTab() {
  const { sessions, activeSession, fetchSessions, executeSession, pauseSession, cancelSession, loading } = useEngineeringStore()

  useEffect(() => { fetchSessions() }, [])

  if (loading && sessions.length === 0) return <div style={{ padding: 16, color: '#9ca3af' }}>—</div>

  return (
    <div style={{ padding: 16 }}>
      <h3 style={{ margin: '0 0 12px', fontSize: 15, color: '#e2e8f0' }}>Execution Sessions</h3>

      {sessions.length === 0 && (
        <div style={{ color: '#9ca3af', fontSize: 13 }}>No execution sessions. Approve a plan first, then create a session.</div>
      )}

      {sessions.map((s) => (
        <div key={s.session_id} style={{ background: '#0f172a', padding: 12, borderRadius: 6, border: '1px solid #1e293b', marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div style={{ color: '#e2e8f0', fontSize: 13, fontFamily: 'monospace' }}>{s.session_id}</div>
            <span style={{ color: STATUS_COLORS[s.status] || '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>{s.status}</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 8 }}>
            <div>
              <div style={{ fontSize: 11, color: '#6b7280' }}>Artifacts</div>
              <div style={{ color: '#e2e8f0', fontSize: 13 }}>{s.artifacts.length}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#6b7280' }}>Workers</div>
              <div style={{ color: '#e2e8f0', fontSize: 13 }}>{Object.keys(s.worker_assignments).length}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#6b7280' }}>Targets</div>
              <div style={{ color: '#e2e8f0', fontSize: 13 }}>{s.workspace_targets.length > 0 ? s.workspace_targets.join(', ') : 'none'}</div>
            </div>
          </div>

          {s.errors.length > 0 && (
            <div style={{ background: '#7f1d1d', padding: 8, borderRadius: 4, marginBottom: 8 }}>
              {s.errors.map((e, i) => (
                <div key={i} style={{ color: '#fca5a5', fontSize: 11 }}>{e}</div>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: 6 }}>
            {s.status === 'planned' && (
              <button onClick={() => executeSession(s.session_id)} disabled={loading} style={{ padding: '4px 12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>
                Execute
              </button>
            )}
            {s.status === 'executing' && (
              <button onClick={() => pauseSession(s.session_id)} disabled={loading} style={{ padding: '4px 12px', background: '#f59e0b', color: '#000', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>
                Pause
              </button>
            )}
            {!['approved', 'rejected', 'cancelled'].includes(s.status) && (
              <button onClick={() => cancelSession(s.session_id)} disabled={loading} style={{ padding: '4px 12px', background: '#374151', color: '#9ca3af', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>
                Cancel
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function ReviewTab() {
  const { proofPackage, fetchReviews, approveReview, rejectReview, loading } = useEngineeringStore()

  useEffect(() => { fetchReviews() }, [])

  if (loading && !proofPackage) return <div style={{ padding: 16, color: '#9ca3af' }}>—</div>

  if (!proofPackage) {
    return <div style={{ padding: 16, color: '#9ca3af' }}>No proof packages awaiting review. Execute a session first.</div>
  }

  const pkg = proofPackage
  const diffSummary = pkg.diff_summary as Record<string, unknown>

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: 15, color: '#e2e8f0' }}>Proof Package Review</h3>
        <span style={{ color: STATUS_COLORS[pkg.review_status] || '#6b7280', fontSize: 12, textTransform: 'uppercase' }}>
          {pkg.review_status}
        </span>
      </div>

      <div style={{ background: '#0f172a', padding: 12, borderRadius: 6, border: '1px solid #1e293b', marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: '#9ca3af' }}>System Recommendation</div>
          <span style={{
            color: RECOMMENDATION_COLORS[pkg.operator_recommendation] || '#6b7280',
            fontSize: 13,
            fontWeight: 600,
            textTransform: 'uppercase',
          }}>
            {pkg.operator_recommendation.replace(/_/g, ' ')}
          </span>
        </div>
        {pkg.recommendation_reasoning.length > 0 && (
          <div style={{ marginTop: 4 }}>
            {pkg.recommendation_reasoning.map((r, i) => (
              <div key={i} style={{ color: '#94a3b8', fontSize: 11, marginTop: 2 }}>{r}</div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 12 }}>
        <div style={{ background: '#0f172a', padding: 10, borderRadius: 6, border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 20, color: '#e2e8f0' }}>{(diffSummary.total_files as number) || 0}</div>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>Files Changed</div>
        </div>
        <div style={{ background: '#0f172a', padding: 10, borderRadius: 6, border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 20, color: '#e2e8f0' }}>{pkg.artifacts.length}</div>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>Artifacts</div>
        </div>
        <div style={{ background: '#0f172a', padding: 10, borderRadius: 6, border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 20, color: pkg.risk_summary.length > 0 ? '#ef4444' : '#22c55e' }}>{pkg.risk_summary.length}</div>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>Risks</div>
        </div>
      </div>

      {pkg.validation_results.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 6 }}>Validation</div>
          {pkg.validation_results.map((vr, i) => {
            const passed = (vr as Record<string, unknown>).passed as boolean
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: passed ? '#22c55e' : '#ef4444', display: 'inline-block' }} />
                <span style={{ color: '#94a3b8', fontSize: 11 }}>{(vr as Record<string, unknown>).file_path as string || (vr as Record<string, unknown>).artifact_id as string}</span>
              </div>
            )
          })}
        </div>
      )}

      {pkg.risk_summary.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 6 }}>Risks</div>
          {pkg.risk_summary.map((risk, i) => (
            <div key={i} style={{ background: '#1c1917', padding: 8, borderRadius: 4, marginBottom: 4, borderLeft: `3px solid ${RISK_COLORS[(risk as Record<string, unknown>).level as string] || '#6b7280'}` }}>
              <div style={{ color: '#e2e8f0', fontSize: 12 }}>{(risk as Record<string, unknown>).description as string}</div>
            </div>
          ))}
        </div>
      )}

      {pkg.trace_ids.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 4 }}>Trace IDs</div>
          <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#6b7280' }}>
            {pkg.trace_ids.join(', ')}
          </div>
        </div>
      )}

      {pkg.review_status === 'pending' && (
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => approveReview(pkg.proof_id)}
            disabled={loading}
            style={{ padding: '8px 20px', background: '#22c55e', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}
          >
            Approve
          </button>
          <button
            onClick={() => rejectReview(pkg.proof_id)}
            disabled={loading}
            style={{ padding: '8px 20px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}
          >
            Reject
          </button>
        </div>
      )}
    </div>
  )
}

export function EngineeringPanel() {
  const { activeTab, setActiveTab, error } = useEngineeringStore()

  return (
    <div style={{ height: '100%', overflow: 'auto', background: '#020617' }}>
      <TabBar active={activeTab} onSelect={(t) => setActiveTab(t as 'intent' | 'plan' | 'queue' | 'sessions' | 'review' | 'gaps')} />
      {error && (
        <div style={{ padding: '8px 16px', background: '#7f1d1d', color: '#fca5a5', fontSize: 12, margin: '0 16px 8px' }}>
          {error}
        </div>
      )}
      {activeTab === 'intent' && <IntentTab />}
      {activeTab === 'plan' && <PlanTab />}
      {activeTab === 'queue' && <QueueTab />}
      {activeTab === 'sessions' && <SessionsTab />}
      {activeTab === 'review' && <ReviewTab />}
      {activeTab === 'gaps' && <GapsTab />}
    </div>
  )
}
