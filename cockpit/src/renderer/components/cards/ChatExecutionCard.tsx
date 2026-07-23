// Chat execution card — STATUS-ONLY. Like PlanSummaryCard, this card carries NO
// approve/reject/authorize/cancel controls: execution decisions live in the Top
// HUD (the sole authorization surface), never in chat. This card reports status,
// concise progress, and links out to the Execution surface / the Task / the
// Proof. Additive-only: renders nothing unless the execution_status surface
// marker is present.
import { ExternalLink, ShieldCheck } from 'lucide-react'

export interface ExecutionCardMetadata {
  surface: 'execution_status'
  plan_record_id?: string
  decision_ref?: string
  state?: string
  execution_state?: string
  attempt_ids?: string[]
  proof_id?: string
  tasks_complete?: number
  tasks_total?: number
}

const STATUS_LINES: Record<string, string> = {
  authorization_requested: 'EXECUTION DECISION SURFACED — AWAITING AUTHORIZATION',
  execution_authorization_pending: 'EXECUTION DECISION SURFACED — AWAITING AUTHORIZATION',
  authorized: 'EXECUTION AUTHORIZED — NOT STARTED',
  running: 'EXECUTION RUNNING',
  blocked: 'EXECUTION BLOCKED — DECISION NEEDED',
  complete: 'EXECUTION COMPLETE — PROOF ATTACHED',
  failed: 'EXECUTION FAILED — RETRY AVAILABLE',
  cancelled: 'EXECUTION CANCELLED',
}

/** Narrow a loose metadata bag to the execution-status shape. Returns null when
 *  the surface marker is absent (additive-only). */
export function asExecutionMetadata(
  metadata: Record<string, unknown> | undefined,
): ExecutionCardMetadata | null {
  if (!metadata) return null
  if (metadata.surface !== 'execution_status') return null
  return metadata as unknown as ExecutionCardMetadata
}

function execRootDataState(meta: ExecutionCardMetadata): string {
  return meta.execution_state || meta.state || 'authorization_requested'
}

export function ChatExecutionCard({
  metadata,
  onOpenExecution,
  onOpenTask,
  onOpenProof,
}: {
  metadata: ExecutionCardMetadata
  onOpenExecution?: () => void
  onOpenTask?: () => void
  onOpenProof?: (proofId: string) => void
}) {
  const state = execRootDataState(metadata)
  const statusLine = STATUS_LINES[state] || 'EXECUTION'
  const total = metadata.tasks_total ?? (metadata.attempt_ids?.length || 0)
  const complete = metadata.tasks_complete ?? 0

  return (
    <div
      data-testid="w2-exec-card-root"
      data-state={state}
      data-plan-record-id={metadata.plan_record_id}
      className="mt-2 rounded border border-border bg-surface/40 p-2 text-[11px] font-mono"
    >
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-3.5 w-3.5 text-cyan" />
        <span className="font-semibold tracking-wide text-text-secondary">{statusLine}</span>
      </div>
      {total > 0 && (
        <div className="mt-1 text-text-tertiary">
          {complete} of {total} task(s) complete
        </div>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button
          type="button"
          data-testid="w2-open-execution-btn"
          onClick={() => onOpenExecution?.()}
          className="inline-flex items-center gap-1 rounded bg-surface px-2 py-0.5 text-text-secondary hover:text-text-primary"
        >
          <ExternalLink className="h-3 w-3" /> Open Execution
        </button>
        <button
          type="button"
          data-testid="w2-open-task-btn"
          onClick={() => onOpenTask?.()}
          className="inline-flex items-center gap-1 rounded bg-surface px-2 py-0.5 text-text-secondary hover:text-text-primary"
        >
          <ExternalLink className="h-3 w-3" /> Open Task
        </button>
        {metadata.proof_id && (
          <button
            type="button"
            data-testid="w2-proof-link"
            onClick={() => onOpenProof?.(metadata.proof_id as string)}
            className="inline-flex items-center gap-1 rounded bg-green-400/10 px-2 py-0.5 text-green-400 hover:text-green-300"
          >
            <ShieldCheck className="h-3 w-3" /> Proof
          </button>
        )}
      </div>
    </div>
  )
}
