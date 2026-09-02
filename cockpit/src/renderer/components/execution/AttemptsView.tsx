// The canonical Execution attempts view — queued/active/completed attempts, the
// authorized frontier, assignment + environment lease + verification + Proof,
// and governed cancel/retry. Reads from the executionAttemptStore (persistence-
// by-refetch; no client-side execution state store). Execution DECISIONS are not
// here — they are HUD-only.
import { useEffect, useState } from 'react'
import { usePolling } from '../../hooks/usePolling'
import {
  useExecutionAttemptStore,
  type AttemptRow,
  type AttemptDetail,
} from '../../stores/executionAttemptStore'

const STATUS_COLOR: Record<string, string> = {
  running: 'text-cyan',
  dispatched: 'text-cyan',
  leased: 'text-warn',
  ready: 'text-text-secondary',
  created: 'text-text-tertiary',
  verifying: 'text-warn',
  succeeded: 'text-ok',
  failed: 'text-danger',
  blocked: 'text-danger',
  cancelled: 'text-text-tertiary',
  rolled_back: 'text-text-tertiary',
}

export function AttemptsView() {
  const attempts = useExecutionAttemptStore((s) => s.attempts)
  const frontier = useExecutionAttemptStore((s) => s.frontier)
  const fetchAttempts = useExecutionAttemptStore((s) => s.fetchAttempts)
  const fetchFrontier = useExecutionAttemptStore((s) => s.fetchFrontier)
  const [selected, setSelected] = useState<string | null>(null)

  usePolling(() => { fetchAttempts(); fetchFrontier() }, 4000)
  useEffect(() => { fetchAttempts(); fetchFrontier() }, [fetchAttempts, fetchFrontier])

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Left: frontier + attempt rows */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <section>
          <h3 className="wv-label mb-1">Authorized frontier</h3>
          {frontier.length === 0 && <p className="text-[10px] text-text-tertiary">No authorized tasks.</p>}
          {frontier.map((f) => (
            <div key={f.packet_id} className="text-[10px] font-mono text-text-secondary flex gap-2">
              <span className="text-text-tertiary">{f.packet_id}</span>
              <span>{f.attempt_count} attempt(s)</span>
              {f.active && <span className="text-cyan">active</span>}
            </div>
          ))}
        </section>

        <section>
          <h3 className="wv-label mb-1">Attempts</h3>
          {attempts.length === 0 && <p className="text-[10px] text-text-tertiary">No attempts yet.</p>}
          <div className="space-y-1">
            {attempts.map((a) => (
              <AttemptRowCard key={a.attempt_id} row={a} onSelect={() => setSelected(a.attempt_id)} selected={selected === a.attempt_id} />
            ))}
          </div>
        </section>
      </div>

      {/* Right: attempt drawer */}
      <div className="w-96 border-l border-border overflow-y-auto bg-canvas">
        {selected ? <AttemptDrawer attemptId={selected} /> : (
          <div className="p-3 text-[10px] text-text-tertiary">Select an attempt to inspect its assignment, environment, verification, and Proof.</div>
        )}
      </div>
    </div>
  )
}

function AttemptRowCard({ row, onSelect, selected }: { row: AttemptRow; onSelect: () => void; selected: boolean }) {
  const color = STATUS_COLOR[row.status] ?? 'text-text-secondary'
  return (
    <button
      type="button"
      data-testid="w2-execution-attempt"
      data-attempt-id={row.attempt_id}
      data-status={row.status}
      onClick={onSelect}
      className={`w-full text-left px-2 py-1 rounded border text-[10px] font-mono ${selected ? 'border-cyan bg-cyan/5' : 'border-border bg-surface/30'}`}
    >
      <div className="flex items-center gap-2">
        <span className="text-text-tertiary">{row.task_id}</span>
        <span className="text-text-tertiary">#{row.attempt_number}</span>
        <span className={color}>{row.status}</span>
        {row.worker_identity && <span className="text-text-tertiary truncate">{row.worker_identity}</span>}
        {row.proof_id && <span data-testid="w2-proof-link" className="text-ok ml-auto">proof</span>}
      </div>
      {row.blocked_reason && <div className="text-danger mt-0.5">{row.blocked_reason}</div>}
    </button>
  )
}

function AttemptDrawer({ attemptId }: { attemptId: string }) {
  const fetchAttempt = useExecutionAttemptStore((s) => s.fetchAttempt)
  const cancel = useExecutionAttemptStore((s) => s.cancel)
  const retry = useExecutionAttemptStore((s) => s.retry)
  const detail = useExecutionAttemptStore((s) => s.attemptById[attemptId] as AttemptDetail | undefined)

  useEffect(() => { fetchAttempt(attemptId) }, [attemptId, fetchAttempt])

  if (!detail) return <div className="p-3 text-[10px] text-text-tertiary">Loading…</div>
  const asn = (detail.assignment ?? {}) as Record<string, unknown>
  const lease = (detail.environment_lease ?? {}) as Record<string, unknown>

  return (
    <div className="p-3 space-y-3 text-[10px] font-mono">
      <div>
        <div className="text-text-secondary">{detail.task_id} · attempt #{detail.attempt_number}</div>
        <div className={STATUS_COLOR[detail.status] ?? 'text-text-secondary'}>{detail.status}</div>
      </div>

      <section data-testid="w2-assignment">
        <h4 className="wv-label mb-1">Assignment</h4>
        <Row label="role" value={String(asn.role_contract_id ?? '—')} />
        <Row label="worker" value={String(asn.worker_identity ?? detail.worker_identity ?? '—')} />
        <Row label="model" value={String((asn.model_profile as Record<string, unknown>)?.model ?? '—')} />
        <Row label="verifier" value={String(asn.verifier_role_id ?? detail.verifier_role_id ?? '—')} />
        <div data-testid="w2-worker-status" className="text-text-tertiary">worker: {detail.worker_identity || '—'}</div>
      </section>

      <section data-testid="w2-environment-lease">
        <h4 className="wv-label mb-1">Environment lease</h4>
        <Row label="lease" value={String(lease.lease_id ?? detail.lease_id ?? '—')} />
        <Row label="worktree" value={String(lease.worktree_path ?? '—')} />
        <Row label="state" value={String(lease.status ?? '—')} />
      </section>

      <section data-testid="w2-verification-status">
        <h4 className="wv-label mb-1">Verification</h4>
        <Row label="proof" value={detail.proof_id || '—'} />
        {detail.proof_id && <a data-testid="w2-proof-link" className="text-ok">Proof {detail.proof_id}</a>}
      </section>

      <div className="flex gap-2 pt-1">
        {detail.cancel_allowed && (
          <button
            type="button"
            data-testid="w2-execution-cancel"
            onClick={() => cancel(attemptId, 'operator cancel')}
            className="text-[10px] px-2 py-1 rounded bg-red-600/20 text-red-400"
          >
            Cancel
          </button>
        )}
        {detail.retry_allowed && (
          <button
            type="button"
            data-testid="w2-execution-retry"
            onClick={() => retry(attemptId)}
            className="text-[10px] px-2 py-1 rounded bg-cyan/10 text-cyan"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-text-tertiary w-16">{label}</span>
      <span className="text-text-secondary truncate">{value}</span>
    </div>
  )
}
