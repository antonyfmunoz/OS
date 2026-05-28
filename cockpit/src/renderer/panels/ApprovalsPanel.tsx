import { useApprovalStore } from '../stores/approvalStore'
import { useOrganismStore } from '../stores/organismStore'
import { usePolling } from '../hooks/usePolling'

const RISK_COLORS = {
  LOW: 'var(--color-ok)',
  MEDIUM: 'var(--color-warn)',
  HIGH: 'var(--color-danger)',
  CRITICAL: 'var(--color-danger)',
} as const

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
  const fetchPending = useOrganismStore((s) => s.fetchPending)
  const fetchCompleted = useOrganismStore((s) => s.fetchCompleted)
  const approveEnvelope = useOrganismStore((s) => s.approveEnvelope)
  const rejectEnvelope = useOrganismStore((s) => s.rejectEnvelope)

  usePolling(() => { fetchApprovals(); fetchPending(); fetchCompleted() }, 3000)

  const pending = approvals.filter((a) => a.status === 'pending')
  const history = approvals.filter((a) => a.status !== 'pending')
  const totalPending = pending.length + spineEnvelopes.length

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold">Governance Gate</h2>
        {totalPending > 0 && (
          <span className="ml-2 px-2 py-0.5 text-xs font-mono rounded bg-cyan-glow text-cyan">
            {totalPending} pending
          </span>
        )}
      </div>

      {/* Spine Pending Envelopes */}
      {spineEnvelopes.length > 0 && (
        <section className="mb-6">
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
                </div>
                <p className="text-sm mb-3">{env.intent}</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => approveEnvelope(env.envelope_id)}
                    className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-ok text-text-inverse transition-colors"
                  >
                    approve
                  </button>
                  <button
                    onClick={() => rejectEnvelope(env.envelope_id)}
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
        <section className="mb-6">
          <h3 className="wv-label mb-3">Pending Approval</h3>
          <div className="space-y-2">
            {pending.map((item) => (
              <div key={item.id} className="wv-card px-4 py-3">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="px-1.5 py-0.5 text-xs font-mono uppercase rounded"
                    style={{
                      color: RISK_COLORS[item.risk_level],
                      background: `${RISK_COLORS[item.risk_level]}15`,
                      border: `1px solid ${RISK_COLORS[item.risk_level]}30`,
                    }}
                  >
                    {item.risk_level}
                  </span>
                  <span className="text-xs text-text-tertiary">from {item.agent}</span>
                </div>
                <p className="text-sm mb-3">{item.description}</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => approve(item.id)}
                    className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-ok text-text-inverse transition-colors"
                  >
                    approve
                  </button>
                  <button
                    onClick={() => deny(item.id)}
                    className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-surface-overlay text-danger border border-border transition-colors"
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
        <div className="mb-6 text-center py-8">
          <p className="text-sm text-text-tertiary">All clear — no pending approvals</p>
        </div>
      )}

      {/* Spine Completed History */}
      {completedEnvelopes.length > 0 && (
        <section className="mb-6">
          <h3 className="wv-label mb-3">Spine History</h3>
          <div className="space-y-1.5">
            {completedEnvelopes.slice(0, 15).map((env) => (
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

      {/* Legacy Decision History */}
      <section>
        <h3 className="wv-label mb-3">Decision History</h3>
        {history.length === 0 ? (
          <p className="text-xs text-text-tertiary">No decisions recorded</p>
        ) : (
          <div className="space-y-1.5">
            {history.map((item) => (
              <div key={item.id} className="flex items-center gap-2 px-3 py-2 rounded bg-surface">
                <span className={`w-2 h-2 rounded-full shrink-0 ${item.status === 'approved' ? 'bg-ok' : 'bg-danger'}`} />
                <p className="text-sm flex-1 truncate">{item.description}</p>
                <span className="wv-label">{item.status}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
