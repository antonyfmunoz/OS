import { useApprovalStore } from '../stores/approvalStore'
import { usePolling } from '../hooks/usePolling'

const RISK_COLORS = {
  LOW: 'var(--accent-green)',
  MEDIUM: 'var(--accent-amber)',
  HIGH: 'var(--accent-red)',
  CRITICAL: 'var(--accent-red)',
} as const

export function ApprovalsPanel() {
  const approvals = useApprovalStore((s) => s.approvals)
  const fetchApprovals = useApprovalStore((s) => s.fetchApprovals)
  const approve = useApprovalStore((s) => s.approve)
  const deny = useApprovalStore((s) => s.deny)

  usePolling(fetchApprovals, 5000)

  const pending = approvals.filter((a) => a.status === 'pending')
  const history = approvals.filter((a) => a.status !== 'pending')

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold">Governance Gate</h2>
        {pending.length > 0 && (
          <span
            className="ml-2 px-2 py-0.5 text-xs font-mono rounded"
            style={{ background: 'var(--glow-cyan)', color: 'var(--accent-cyan)' }}
          >
            {pending.length} pending
          </span>
        )}
      </div>

      {/* Pending */}
      {pending.length > 0 && (
        <section className="mb-6">
          <h3 className="hud-text mb-3">Pending Approval</h3>
          <div className="space-y-2">
            {pending.map((item) => (
              <div
                key={item.id}
                className="px-4 py-3 rounded"
                style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
              >
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
                  <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                    from {item.agent}
                  </span>
                </div>
                <p className="text-sm mb-3">{item.description}</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => approve(item.id)}
                    className="px-3 py-1.5 text-xs font-mono uppercase rounded transition-colors"
                    style={{ background: 'var(--accent-green)', color: 'var(--bg)' }}
                  >
                    approve
                  </button>
                  <button
                    onClick={() => deny(item.id)}
                    className="px-3 py-1.5 text-xs font-mono uppercase rounded transition-colors"
                    style={{ background: 'var(--surface-3)', color: 'var(--accent-red)', border: '1px solid var(--border)' }}
                  >
                    deny
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* History */}
      <section>
        <h3 className="hud-text mb-3">Decision History</h3>
        {history.length === 0 ? (
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>No decisions recorded</p>
        ) : (
          <div className="space-y-1.5">
            {history.map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-2 px-3 py-2 rounded"
                style={{ background: 'var(--surface-1)' }}
              >
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{
                    background: item.status === 'approved' ? 'var(--accent-green)' : 'var(--accent-red)',
                  }}
                />
                <p className="text-sm flex-1 truncate">{item.description}</p>
                <span className="hud-text">{item.status}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
