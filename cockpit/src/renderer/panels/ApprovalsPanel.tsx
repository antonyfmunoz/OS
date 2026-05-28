import { useState } from 'react'
import { useApprovalStore } from '../stores/approvalStore'
import { useOrganismStore } from '../stores/organismStore'
import { useRealtimeStore } from '../stores/realtimeStore'
import { usePolling } from '../hooks/usePolling'
import { ConnectionBanner } from '../components/ConnectionBanner'
import { relativeTime } from '../lib/time'

const RISK_BADGE: Record<string, string> = {
  low: 'wv-badge-ok',
  medium: 'wv-badge-warn',
  high: 'wv-badge-danger',
  critical: 'wv-badge-danger',
}

export function ApprovalsPanel() {
  const approvals = useApprovalStore((s) => s.approvals)
  const fetchApprovals = useApprovalStore((s) => s.fetchApprovals)
  const approve = useApprovalStore((s) => s.approve)
  const deny = useApprovalStore((s) => s.deny)

  const spineEnvelopes = useOrganismStore((s) => s.pendingEnvelopes)
  const completedEnvelopes = useOrganismStore((s) => s.completedEnvelopes)
  const gateway = useOrganismStore((s) => s.gateway)
  const guard = useOrganismStore((s) => s.guard)
  const executionMode = useOrganismStore((s) => s.executionMode)
  const gatewayDecisions = useOrganismStore((s) => s.gatewayDecisions)
  const fetchPending = useOrganismStore((s) => s.fetchPending)
  const fetchCompleted = useOrganismStore((s) => s.fetchCompleted)
  const fetchGateway = useOrganismStore((s) => s.fetchGateway)
  const fetchGuard = useOrganismStore((s) => s.fetchGuard)
  const fetchGatewayDecisions = useOrganismStore((s) => s.fetchGatewayDecisions)
  const fetchExecutionMode = useOrganismStore((s) => s.fetchExecutionMode)
  const approveEnvelope = useOrganismStore((s) => s.approveEnvelope)
  const rejectEnvelope = useOrganismStore((s) => s.rejectEnvelope)

  const realtimeStatus = useRealtimeStore((s) => s.status)

  const [rejectReason, setRejectReason] = useState<Record<string, string>>({})

  usePolling(() => { fetchApprovals(); fetchPending(); fetchCompleted(); fetchGateway(); fetchGuard(); fetchGatewayDecisions(); fetchExecutionMode() },
    realtimeStatus === 'connected' ? 10000 : 3000)

  const pending = approvals.filter((a) => a.status === 'pending')
  const history = approvals.filter((a) => a.status !== 'pending')
  const totalPending = pending.length + spineEnvelopes.length

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />

      <div className="flex items-center px-4 py-3 flex-shrink-0 border-b border-border">
        <h2 className="text-lg font-semibold">Governance Gate</h2>
        {totalPending > 0 && (
          <span className="ml-2 px-2 py-0.5 text-xs font-mono rounded bg-cyan-glow text-cyan">
            {totalPending} pending
          </span>
        )}
        <div className="ml-auto flex gap-4 text-[10px]">
          {executionMode && (
            <span className="text-cyan font-mono">MODE: {executionMode.current_mode.toUpperCase()}</span>
          )}
          {gateway && (
            <span className="text-text-secondary">
              GATEWAY: {gateway.policy} · {gateway.total_auto_executed} auto · {gateway.total_blocked} blocked
            </span>
          )}
          {guard && (
            <span className="text-text-secondary">
              GUARD: {guard.mode.replace(/_/g, ' ')} · {guard.total_blocked} blocked
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left: pending + approval actions */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Spine Pending Envelopes */}
          {spineEnvelopes.length > 0 && (
            <section>
              <h3 className="wv-label mb-3">Spine Pending — {spineEnvelopes.length}</h3>
              <div className="space-y-2">
                {spineEnvelopes.map((env) => (
                  <div key={env.envelope_id} className="wv-card px-4 py-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`wv-badge ${RISK_BADGE[env.risk_level] ?? 'wv-badge-ok'}`}>
                        {env.risk_level.toUpperCase()}
                      </span>
                      <span className="text-xs text-text-tertiary">from {env.source}</span>
                      <span className="text-xs text-text-tertiary">· {env.action_type}</span>
                      <span className="text-xs text-text-tertiary">· blast: {env.blast_radius}</span>
                    </div>
                    <p className="text-sm mb-2">{env.intent}</p>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        placeholder="rejection reason (optional)"
                        className="flex-1 text-xs px-2 py-1 rounded bg-surface border border-border text-text-primary"
                        value={rejectReason[env.envelope_id] ?? ''}
                        onChange={(e) => setRejectReason((prev) => ({ ...prev, [env.envelope_id]: e.target.value }))}
                      />
                      <button
                        onClick={() => approveEnvelope(env.envelope_id)}
                        className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-ok text-text-inverse transition-colors"
                      >
                        approve
                      </button>
                      <button
                        onClick={() => rejectEnvelope(env.envelope_id, rejectReason[env.envelope_id] || undefined)}
                        className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-surface-overlay text-danger border border-border transition-colors"
                      >
                        reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Legacy Pending */}
          {pending.length > 0 && (
            <section>
              <h3 className="wv-label mb-3">Legacy Pending — {pending.length}</h3>
              <div className="space-y-2">
                {pending.map((item) => (
                  <div key={item.id} className="wv-card px-4 py-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`wv-badge ${RISK_BADGE[item.risk_level?.toLowerCase()] ?? 'wv-badge-ok'}`}>
                        {item.risk_level}
                      </span>
                      <span className="text-xs text-text-tertiary">from {item.agent}</span>
                    </div>
                    <p className="text-sm mb-3">{item.description}</p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => approve(item.id)}
                        className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-ok text-text-inverse"
                      >
                        approve
                      </button>
                      <button
                        onClick={() => deny(item.id)}
                        className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-surface-overlay text-danger border border-border"
                      >
                        deny
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {totalPending === 0 && (
            <div className="text-center py-8">
              <p className="text-sm text-text-tertiary">All clear — no pending approvals</p>
            </div>
          )}

          {/* Spine Completed History */}
          {completedEnvelopes.length > 0 && (
            <section>
              <h3 className="wv-label mb-3">Spine History</h3>
              <div className="space-y-1.5">
                {completedEnvelopes.slice(0, 20).map((env) => (
                  <div key={env.envelope_id} className="flex items-center gap-2 px-3 py-2 rounded bg-surface">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${env.result_success ? 'bg-ok' : 'bg-danger'}`} />
                    <p className="text-sm flex-1 truncate">{env.intent}</p>
                    <span className={`wv-badge ${RISK_BADGE[env.risk_level] ?? 'wv-badge-ok'} text-[9px]`}>
                      {env.risk_level}
                    </span>
                    <span className="wv-label">{env.status}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Right: gateway decisions + guard violations */}
        <div className="w-80 border-l border-border overflow-y-auto p-3 space-y-4 bg-canvas">
          {/* Gateway decisions */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Gateway Decisions</h3>
            {gateway && (
              <div className="flex gap-3 mb-2 text-[10px]">
                <span className="text-ok">{gateway.total_auto_executed} auto</span>
                <span className="text-danger">{gateway.total_blocked} blocked</span>
                <span className="text-warn">{gateway.total_recommended} recommend</span>
              </div>
            )}
            <div className="space-y-1">
              {gatewayDecisions.length === 0 && <p className="text-xs text-text-tertiary">No decisions recorded</p>}
              {gatewayDecisions.slice(0, 15).map((d, i) => (
                <div key={i} className="flex items-center gap-2 py-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    d.action === 'allowed' ? 'bg-ok' : d.action === 'blocked' ? 'bg-danger' : 'bg-warn'
                  }`} />
                  <span className="text-[11px] text-text-primary truncate flex-1">{d.intent}</span>
                  <span className="text-[10px] text-text-tertiary">{d.action}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Guard violations */}
          <section className="wv-card p-3">
            <h3 className="wv-label mb-2">Spine Guard</h3>
            {guard ? (
              <>
                <div className="flex gap-3 mb-2 text-[10px]">
                  <span className="text-cyan font-mono">{guard.mode.replace(/_/g, ' ').toUpperCase()}</span>
                  <span className="text-text-secondary">{guard.total_allowed} allowed</span>
                  <span className="text-danger">{guard.total_blocked} blocked</span>
                </div>
                <div className="space-y-1">
                  {guard.recent_violations.length === 0 && <p className="text-xs text-text-tertiary">No violations</p>}
                  {guard.recent_violations.slice(0, 10).map((v, i) => (
                    <div key={i} className="text-[10px] text-danger/80 truncate py-0.5">
                      {v.source}: {v.reason}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-xs text-text-tertiary">Guard not initialized</p>
            )}
          </section>

          {/* Decision History (legacy) */}
          {history.length > 0 && (
            <section className="wv-card p-3">
              <h3 className="wv-label mb-2">Legacy History</h3>
              <div className="space-y-1">
                {history.slice(0, 10).map((item) => (
                  <div key={item.id} className="flex items-center gap-2 py-0.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${item.status === 'approved' ? 'bg-ok' : 'bg-danger'}`} />
                    <span className="text-[11px] text-text-primary truncate flex-1">{item.description}</span>
                    <span className="text-[10px] text-text-tertiary">{item.status}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
