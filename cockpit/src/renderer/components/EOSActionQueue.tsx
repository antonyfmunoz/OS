// EOS projection action queue — WP-P4-EOS-ACTION-QUEUE-COCKPIT-001.
//
// Operator surface over the governed EOS action lifecycle, rendered inside
// the same Governance Gate panel as every other UMH approval. Button rules
// are server-authoritative: approve/reject only on server-reported `pending`
// rows; execute only when the server marks the row `execute_enabled` (the
// #185 approved + non-provider allowlist contract). No local status
// transitions — every state shown comes from a server response.
import { useState } from 'react'
import { useEOSActionQueueStore } from '../stores/eosActionQueueStore'
import type { EOSActionProposal, EOSActionResult } from '../stores/eosActionQueueStore'

const STATUS_BADGE: Record<string, string> = {
  pending: 'wv-badge-warn',
  approved: 'wv-badge-ok',
  executing: 'wv-badge-warn',
  completed: 'wv-badge-ok',
  rejected: 'wv-badge-danger',
  failed: 'wv-badge-danger',
}

function ResultBlock({ result }: { result: EOSActionResult }) {
  const applied = result.execution_applied ?? result.decision_applied
  return (
    <div className="mt-2 px-3 py-2 rounded bg-surface text-[11px] font-mono space-y-0.5" data-testid={`eos-result-${result.proposal_id}`}>
      <div className={applied ? 'text-ok' : 'text-danger'}>
        {result.surface}: {applied ? 'applied' : 'not applied'}
        {result.new_status ? ` · ${result.prior_status ?? '?'} → ${result.new_status}` : ''}
      </div>
      {result.decided_at && <div className="text-text-secondary">decided_at: {result.decided_at}</div>}
      {result.executed_at && <div className="text-text-secondary">executed_at: {result.executed_at}</div>}
      {result.result_ref && <div className="text-text-secondary">result_ref: {result.result_ref}</div>}
      {result.envelope_id && <div className="text-text-tertiary">envelope: {result.envelope_id}</div>}
      {result.governance_status && <div className="text-text-tertiary">governance: {result.governance_status}</div>}
      {result.requeued_for_reapproval && <div className="text-warn">requeued for human re-approval</div>}
      {result.error && <div className="text-danger">error: {result.error}</div>}
    </div>
  )
}

function ProposalRow({ proposal }: { proposal: EOSActionProposal }) {
  const approve = useEOSActionQueueStore((s) => s.approve)
  const reject = useEOSActionQueueStore((s) => s.reject)
  const execute = useEOSActionQueueStore((s) => s.execute)
  const busy = useEOSActionQueueStore((s) => s.busy[proposal.proposal_id] === true)
  const result = useEOSActionQueueStore((s) => s.results[proposal.proposal_id])
  const [reason, setReason] = useState('')

  // Server authority: `pending` comes from the read seam; execute_enabled is
  // computed server-side (approved + #185 non-provider allowlist). The UI
  // never widens either.
  const canDecide = proposal.status === 'pending' && !busy
  const canExecute = proposal.execute_enabled === true && !busy

  return (
    <div className="wv-card px-4 py-3" data-testid={`eos-proposal-${proposal.proposal_id}`}>
      <div className="flex items-center gap-2 mb-1 flex-wrap">
        <span className={`wv-badge ${STATUS_BADGE[proposal.status] ?? 'wv-badge-warn'}`}>
          {proposal.status.toUpperCase()}
        </span>
        <span className="text-[10px] font-mono text-cyan">{proposal.action_type}</span>
        {proposal.target_domain && (
          <span className="text-[10px] text-text-tertiary">domain: {proposal.target_domain}</span>
        )}
        <span className="text-[10px] text-text-tertiary">from {proposal.agent_name ?? proposal.agent_id ?? 'unknown agent'}</span>
        <span className="text-[10px] font-mono text-text-tertiary">{proposal.proposal_id}</span>
      </div>
      <p className="text-sm mb-1">{proposal.requested_operation ?? proposal.action_type}</p>
      {proposal.summary && <p className="text-xs text-text-secondary mb-2">{proposal.summary}</p>}
      <div className="flex gap-3 text-[10px] text-text-tertiary mb-2 flex-wrap">
        {proposal.created_at && <span>created {proposal.created_at}</span>}
        {proposal.updated_at && <span>updated {proposal.updated_at}</span>}
        <span>retries {proposal.retry_count ?? 0}/{proposal.max_retries ?? 0}</span>
        <span>state {proposal.approval_state}</span>
      </div>
      <div className="flex items-center gap-2">
        {canDecide && (
          <input
            type="text"
            placeholder="reason (optional)"
            className="flex-1 text-xs px-2 py-1 rounded bg-surface border border-border text-text-primary"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        )}
        {canDecide && (
          <button
            onClick={() => approve(proposal.proposal_id, reason || undefined)}
            className="px-3 py-2 text-xs font-mono uppercase rounded bg-ok text-text-inverse"
          >
            approve
          </button>
        )}
        {canDecide && (
          <button
            onClick={() => reject(proposal.proposal_id, reason || undefined)}
            className="px-3 py-2 text-xs font-mono uppercase rounded bg-surface-overlay text-danger border border-border"
          >
            reject
          </button>
        )}
        {canExecute && (
          <button
            onClick={() => execute(proposal.proposal_id)}
            className="px-3 py-2 text-xs font-mono uppercase rounded bg-cyan-glow text-cyan border border-border"
          >
            execute
          </button>
        )}
        {busy && <span className="text-[10px] text-text-tertiary">working…</span>}
      </div>
      {result && <ResultBlock result={result} />}
    </div>
  )
}

export function EOSActionQueue() {
  const connectionStatus = useEOSActionQueueStore((s) => s.connectionStatus)
  const sourceBuildSafe = useEOSActionQueueStore((s) => s.sourceBuildSafe)
  const retryPolicy = useEOSActionQueueStore((s) => s.retryPolicy)
  const allowedActionTypes = useEOSActionQueueStore((s) => s.allowedActionTypes)
  const beastHead = useEOSActionQueueStore((s) => s.beastHead)
  const proposals = useEOSActionQueueStore((s) => s.proposals)
  const queueError = useEOSActionQueueStore((s) => s.queueError)
  const fetchProposals = useEOSActionQueueStore((s) => s.fetchProposals)

  return (
    <section data-testid="eos-action-queue">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="wv-label">Projection Actions — EOS{proposals.length > 0 ? ` — ${proposals.length}` : ''}</h3>
        <span className="text-[10px] text-text-tertiary">{connectionStatus}</span>
        <span className={`text-[10px] ${sourceBuildSafe ? 'text-ok' : 'text-danger'}`}>
          {sourceBuildSafe ? 'source build-safe' : 'source not build-safe'}
        </span>
        {beastHead && <span className="text-[10px] font-mono text-text-tertiary">head {beastHead}</span>}
        {retryPolicy && <span className="text-[10px] text-text-tertiary">retry: {retryPolicy}</span>}
        {allowedActionTypes && (
          <span className="text-[10px] text-text-tertiary">executable: {allowedActionTypes}</span>
        )}
        <button
          onClick={() => fetchProposals()}
          className="ml-auto px-2 py-1 text-[10px] font-mono uppercase rounded bg-surface border border-border text-text-secondary"
        >
          refresh
        </button>
      </div>
      {queueError && (
        <p className="text-xs text-danger mb-2" data-testid="eos-queue-error">{queueError}</p>
      )}
      {proposals.length === 0 && !queueError && (
        <p className="text-xs text-text-tertiary">No EOS action proposals</p>
      )}
      <div className="space-y-2">
        {proposals.map((p) => (
          <ProposalRow key={p.proposal_id} proposal={p} />
        ))}
      </div>
    </section>
  )
}
