// Plan summary card — MVP Wave 1. Rendered INSIDE the assistant chat bubble
// whenever an assistant message carries `metadata.surface === 'objective_plan'`
// (see RightRail.tsx MessageBubble).
//
// OWNER DESIGN (final): the chat card is STATUS-ONLY. It shows state, version,
// packet/lane counts, linkage chips, the clarification prompt (clarification is
// conversational, so it stays in chat), and an "Open Plan" navigation action.
// It contains NO approve/reject/cancel controls — all plan DECISIONS live off
// the card: approve/reject in the Top-HUD ControlPanel unified-approval strip,
// cancel in ObjectivePlanPanel. The card reflects server state, never mutates it.
//
// DETERMINISTIC data-state MAPPING (root data-testid="wg-plan-root"):
//   - no plan metadata yet / fetch in flight ....... "rendering"
//   - state 'awaiting_approval' && graph_version === 1 .. "awaiting_approval"
//   - state 'awaiting_approval' && graph_version  >  1 .. "revised"
//         (also sets data-revision={graph_version})
//   - state 'clarification_required' ............... "clarifying"
//   - state 'approved' | 'rejected' | 'cancelled' | 'superseded' | 'failed' .. as-is
// This is ONE deterministic function of (state, graph_version). No other input
// affects data-state.
import {
  GitBranch, ShieldCheck, ExternalLink, HelpCircle,
} from 'lucide-react'
import type {
  ObjectivePlanMetadata,
  ObjectivePlanState,
} from '../../stores/objectivePlanStore'

const APPROVED_EXEC_NOT_STARTED = 'PLAN APPROVED — EXECUTION NOT STARTED'

/** Narrow a loose metadata bag to the objective-plan shape. Returns null when the
 *  surface marker is absent so the caller renders nothing (additive-only). */
export function asObjectivePlanMetadata(
  metadata: Record<string, unknown> | undefined,
): ObjectivePlanMetadata | null {
  if (!metadata) return null
  if (metadata.surface !== 'objective_plan') return null
  if (typeof metadata.plan_record_id !== 'string') return null
  return metadata as unknown as ObjectivePlanMetadata
}

/** The single deterministic (state, graph_version) → data-state function. */
export function planRootDataState(
  state: ObjectivePlanState,
  graphVersion: number,
  fetching: boolean,
): string {
  if (fetching) return 'rendering'
  if (state === 'clarification_required') return 'clarifying'
  if (state === 'awaiting_approval') return graphVersion > 1 ? 'revised' : 'awaiting_approval'
  return state
}

function stateBadgeClass(state: ObjectivePlanState): string {
  switch (state) {
    case 'awaiting_approval': return 'bg-yellow-400/10 text-yellow-400'
    case 'approved': return 'bg-green-400/10 text-green-400'
    case 'rejected': return 'bg-red-400/10 text-red-400'
    case 'cancelled': return 'bg-red-400/10 text-red-400'
    case 'clarification_required': return 'bg-cyan/10 text-cyan'
    case 'superseded': return 'bg-text-tertiary/10 text-text-tertiary'
    case 'failed': return 'bg-red-400/10 text-red-400'
    default: return 'bg-text-tertiary/10 text-text-tertiary'
  }
}

function trunc(id: string | undefined, keep = 10): string {
  if (!id) return ''
  return id.length > keep ? `${id.slice(0, keep)}…` : id
}

export function PlanSummaryCard({
  metadata,
  conversationId,
  onOpenPlan,
}: {
  metadata: ObjectivePlanMetadata
  // Fallback conversation id (the active chat conversation this card renders in),
  // used for data-conversation-id when the backend didn't echo it into metadata.
  conversationId?: string
  onOpenPlan?: () => void
}) {
  const state = metadata.state
  const graphVersion = metadata.graph_version ?? 1
  // The metadata block is fully materialized on the message, so the card is not
  // itself fetching — "rendering" only applies if a plan_record_id is missing.
  const fetching = !metadata.plan_record_id
  const dataState = planRootDataState(state, graphVersion, fetching)
  const isRevision = state === 'awaiting_approval' && graphVersion > 1
  const clarifications = metadata.clarification_questions ?? []
  // DOM-truthed anchors for the field harness's continuity/relaunch checks: the
  // plan record id (always on metadata) and the conversation id (metadata echo or
  // the active conversation fallback). Emitted as data-* so the collector can
  // read them off wg-plan-root without any API call.
  const conversationIdAttr = metadata.conversation_id ?? conversationId

  return (
    <div
      data-testid="wg-plan-root"
      data-state={dataState}
      data-plan-record-id={metadata.plan_record_id}
      {...(conversationIdAttr ? { 'data-conversation-id': conversationIdAttr } : {})}
      {...(isRevision ? { 'data-revision': graphVersion } : {})}
      className="mt-2 rounded border border-border bg-surface p-2"
      style={{ borderLeft: '2px solid var(--color-cyan)' }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <GitBranch size={11} className="text-cyan shrink-0" />
        <span className="text-[9px] font-mono uppercase tracking-wider text-cyan">
          Objective Plan
        </span>
        <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded uppercase ${stateBadgeClass(state)}`}>
          {state.replace(/_/g, ' ')}
        </span>
        <span className="text-[8px] font-mono px-1 rounded bg-surface-raised text-text-tertiary">
          v{graphVersion}
        </span>
        {isRevision && (
          <span className="text-[8px] font-mono px-1 rounded bg-cyan/10 text-cyan">revised</span>
        )}
      </div>

      <div className="flex items-center gap-2 flex-wrap text-[9px] font-mono text-text-tertiary mb-1.5">
        <span className="px-1.5 py-0.5 rounded bg-surface-raised">
          {metadata.packet_count ?? 0} packets
        </span>
        <span className="px-1.5 py-0.5 rounded bg-surface-raised">
          {metadata.lane_count ?? 0} lanes
        </span>
      </div>

      {/* Linkage chips — the plan's provenance across the grounding → gap → graph
          chain. Truncated so they never flood the narrow chat rail. */}
      <div className="flex items-center gap-1 flex-wrap text-[8px] font-mono text-text-tertiary mb-1.5">
        {metadata.intent_id && (
          <span className="px-1 py-0.5 rounded bg-surface-raised" title={`intent: ${metadata.intent_id}`}>
            intent {trunc(metadata.intent_id)}
          </span>
        )}
        {metadata.grounding_snapshot_id && (
          <span className="px-1 py-0.5 rounded bg-surface-raised" title={`grounding: ${metadata.grounding_snapshot_id}`}>
            grounding {trunc(metadata.grounding_snapshot_id)}
          </span>
        )}
        {metadata.gap_model_id && (
          <span className="px-1 py-0.5 rounded bg-surface-raised" title={`gap model: ${metadata.gap_model_id}`}>
            gap {trunc(metadata.gap_model_id)}
          </span>
        )}
      </div>

      {/* Clarification prompt — clarification is conversational, so it stays on the
          chat card. Lists each question with why it is material. */}
      {clarifications.length > 0 && (
        <div
          data-testid="wg-clarification-prompt"
          className="mb-1.5 rounded border border-cyan/30 bg-cyan/5 p-1.5"
        >
          <div className="flex items-center gap-1 text-[9px] font-mono text-cyan mb-1">
            <HelpCircle size={10} />
            clarification required before this plan proceeds
          </div>
          <ul className="space-y-1">
            {clarifications.map((q, i) => (
              <li key={i} className="text-[9px] text-text-secondary">
                <span className="text-text-primary">{q.question}</span>
                {q.why_material && (
                  <span className="text-text-tertiary"> — {q.why_material}</span>
                )}
                {q.dimension && (
                  <span className="ml-1 text-[8px] font-mono px-1 rounded bg-surface-raised text-text-tertiary">
                    {q.dimension}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Honest post-decision status. Approval NEVER auto-starts execution; the
          decision itself happens in the Top-HUD approval strip, not here. */}
      {state === 'approved' && (
        <div className="flex items-center gap-1 mb-1.5 text-[9px] font-mono text-green-400">
          <ShieldCheck size={10} />
          {APPROVED_EXEC_NOT_STARTED}
        </div>
      )}
      {state === 'rejected' && (
        <div className="mb-1.5 text-[9px] font-mono text-red-400">Plan rejected.</div>
      )}
      {state === 'cancelled' && (
        <div className="mb-1.5 text-[9px] font-mono text-red-400">Plan cancelled.</div>
      )}

      <button
        data-testid="wg-open-plan-btn"
        onClick={() => onOpenPlan?.()}
        className="flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded border border-cyan/30 text-cyan hover:bg-cyan-glow transition-colors"
      >
        <ExternalLink size={9} /> Open Plan
      </button>
    </div>
  )
}
