// Objective-plan store — MVP Wave 1 cockpit planning surface.
//
// DOCTRINE (mirrors intentLoopStore.ts): the objective plan originates ONLY on
// the server-side planning rail. An operator types a high-level objective into
// Cockpit Chat; the backend classifies intent === "objective_plan", grounds it,
// builds a gap model, decomposes it into a versioned work-graph plan record, and
// returns a ChatResponse carrying `metadata.surface === "objective_plan"`. This
// store is a DOWNSTREAM control client — it has NO plan-authoring action:
//   - GET  /api/umh/objective-plan                          (surface list)
//   - GET  /api/umh/objective-plan/{id}                     (full detail)
//   - GET  /api/umh/objective-plan/by-conversation/{convId} (detail | null)
//   - GET  /api/umh/objective-plan/{id}/versions            (all versions asc)
//   - POST /api/umh/objective-plan/{id}/decision            (approve/reject/cancel)
// backed by the server's governed_mutation runtime under a registered
// MutationSpec. The store NEVER advances a plan's state client-side — every
// decide() re-reads server truth after the write. Same authed fetch pattern as
// intentLoopStore (fetchApi → Clerk bearer).
import { create } from 'zustand'
import { fetchApi } from '../api/client'

/** Lifecycle state emitted on assistant-message metadata AND on plan records.
 *  Server is the sole authority for transitions; the UI only reflects it. */
export type ObjectivePlanState =
  | 'awaiting_approval'
  | 'approved'
  | 'rejected'
  | 'cancelled'
  | 'clarification_required'
  | 'superseded'
  | 'failed'

/** A single clarification the owner must resolve before the plan can proceed. */
export interface ClarificationQuestion {
  question: string
  why_material: string
  dimension: string
}

/** Metadata block on an assistant ChatMessage when a plan is involved.
 *  This is the exact shape the PlanSummaryCard reads out of `msg.metadata`. */
export interface ObjectivePlanMetadata {
  surface: 'objective_plan'
  state: ObjectivePlanState
  plan_record_id: string
  objective_id: string
  graph_version: number
  // Optional: the backend may echo the conversation id into metadata. When
  // absent, the chat card falls back to the chat store's active conversationId
  // (the card is rendered inside that conversation) so wg-plan-root can always
  // expose data-conversation-id for the field harness's continuity checks.
  conversation_id?: string
  intent_id?: string
  grounding_snapshot_id?: string
  current_state_id?: string
  desired_state_id?: string
  gap_model_id?: string
  workpacket_ids?: string[]
  approval_request_ids?: string[]
  packet_count?: number
  lane_count?: number
  clarification_questions?: ClarificationQuestion[]
}

/** Row shape returned by the surface list + versions endpoints. */
export interface PlanSummary {
  plan_record_id: string
  objective_id: string
  graph_version: number
  status: ObjectivePlanState
  conversation_id: string
  created_at: string
  packet_count: number
  objective_text: string
}

export type PlanNodeKind = 'packet' | 'decision_gate' | 'verification' | 'milestone'

export interface PlanNode {
  node_id: string
  kind: PlanNodeKind
  title: string
  lane: string
  workpacket_id?: string | null
  status: string
  depends_on: string[]
  evidence_refs: string[]
}

/** Server edge shape (compiler.py): `{"from": node_id, "to": node_id}`. */
export interface PlanEdge {
  from: string
  to: string
  type?: string
}

export interface StateStatement {
  statement: string
  evidence_refs?: string[]
  acceptance_criteria?: string[]
}

export interface CurrentState {
  statements: StateStatement[]
  unknowns: string[]
}

export interface DesiredState {
  statements: StateStatement[]
  constraints: string[]
}

export interface GapModelGap {
  gap_id: string
  description: string
  severity: string
}

export interface OwnerDecision {
  question: string
  why_material: string
  dimension: string
}

export interface GapModel {
  gaps: GapModelGap[]
  assumptions: string[]
  contradictions: string[]
  unknowns: string[]
  owner_decisions: OwnerDecision[]
}

export interface PlanPacket {
  packet_id: string
  title?: string
  user_intent?: string
  status: string
  risk_class: string
  dependencies: string[]
  current_state?: string
  desired_state?: string
  success_criteria?: string[]
}

export interface DecisionLogEntry {
  decision: string
  decided_by: string
  /** Server records `decided_at` (epoch seconds); `at` kept for older rows. */
  decided_at?: number | string
  at?: string
  reason?: string | null
  authorization_effect?: string
  status_message?: string
}

/** Plan work-scope — the first-class tenant/target context on a plan record. */
export interface PlanWorkScope {
  tenant_id?: string
  target_kind?: string
  conversation_id?: string
}

/** Fractal decomposition record: how the objective was cut into Tasks and what
 *  was deliberately deferred to child objectives. */
export interface PlanDecomposition {
  decomposition_depth?: number
  decomposition_budget?: number
  decomposition_frontier?: string[]
  deferred_child_objectives?: Array<{ title?: string; gap_key?: string }>
  unresolved_branches?: string[]
  stop_reason?: string
}

/** Archetype policy resolved for the plan — the role/skill contract it runs on. */
export interface PlanArchetypeResolution {
  archetype_id?: string
  archetype_version?: number
  default_role_contract_id?: string
  required_skill_refs?: Array<Record<string, unknown>>
}

/** Development readiness profile — production-layer assessment for the objective. */
export interface PlanDevelopmentProfile {
  target_kind?: string
  governance_profile?: string
  artifact_assessments?: Array<{ artifact_type?: string; status?: string }>
  layer_assessments?: Array<{ layer?: string; status?: string; reason?: string }>
  cross_cutting_assessments?: Array<{ item?: string; status?: string }>
  missing_required_artifacts?: string[]
}

/** Latest readiness assessment snapshot. */
export interface PlanReadinessAssessment {
  state?: string
}

/** Full plan record — the WorkDetailPanel detail view. */
export interface PlanDetail {
  plan_record_id: string
  objective_id: string
  graph_version: number
  status: ObjectivePlanState
  supersedes_plan_record_id?: string | null
  conversation_id: string
  message_id?: string
  intent_id?: string
  grounding_snapshot_id?: string
  current_state_id?: string
  desired_state_id?: string
  gap_model_id?: string
  nodes: PlanNode[]
  edges: PlanEdge[]
  lanes: string[]
  workpacket_ids: string[]
  approval_request_ids: string[]
  decision_log: DecisionLogEntry[]
  current_state?: CurrentState
  desired_state?: DesiredState
  gap_model?: GapModel
  packets: PlanPacket[]
  // Wave 1 §4/§6/§7/§8/§10 — first-class typed plan context.
  work_scope?: PlanWorkScope
  planning_scale?: string
  decomposition?: PlanDecomposition
  archetype_resolution?: PlanArchetypeResolution
  development_profile?: PlanDevelopmentProfile
  readiness_assessment?: PlanReadinessAssessment
  objective_text?: string
  created_at: string
  updated_at: string
}

export type PlanDecision = 'approve' | 'reject' | 'cancel'

interface DecisionResponse {
  ok: boolean
  plan?: PlanDetail
  error?: string
  conflict?: boolean
}

/** Result surfaced to the caller of decide() so a version-conflict can be shown
 *  distinctly from a hard failure. The store always re-fetches server truth. */
export interface PlanDecisionResult {
  ok: boolean
  plan?: PlanDetail
  error?: string | null
  conflict?: boolean
}

interface ObjectivePlanState_ {
  plans: PlanSummary[]
  planById: Record<string, PlanDetail>
  versionsByObjective: Record<string, PlanSummary[]>
  selectedPlanId: string | null
  loading: boolean
  detailLoading: boolean
  error: string | null
  decidingPlanId: string | null

  selectPlan: (planRecordId: string | null) => void
  fetchSurface: () => Promise<void>
  fetchPlan: (planRecordId: string) => Promise<PlanDetail | null>
  fetchByConversation: (conversationId: string) => Promise<PlanDetail | null>
  fetchVersions: (planRecordId: string) => Promise<PlanSummary[]>
  decide: (
    planRecordId: string,
    decision: PlanDecision,
    reason: string | undefined,
    expectedVersion: number,
  ) => Promise<PlanDecisionResult>
}

export const useObjectivePlanStore = create<ObjectivePlanState_>((set, get) => ({
  plans: [],
  planById: {},
  versionsByObjective: {},
  selectedPlanId: null,
  loading: false,
  detailLoading: false,
  error: null,
  decidingPlanId: null,

  selectPlan: (planRecordId) => set({ selectedPlanId: planRecordId }),

  fetchSurface: async () => {
    set({ loading: true })
    try {
      // Backend returns a BARE array of surface rows (objective_plan_routes).
      const data = await fetchApi<PlanSummary[]>('/objective-plan')
      set({ plans: Array.isArray(data) ? data : [], error: null, loading: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false })
    }
  },

  fetchPlan: async (planRecordId: string) => {
    set({ detailLoading: true })
    try {
      // Backend returns the BARE plan dict, or {error: "not_found", ...}.
      const data = await fetchApi<PlanDetail | { error: string }>(
        `/objective-plan/${planRecordId}`,
      )
      const plan = data && !('error' in data) && data.plan_record_id ? (data as PlanDetail) : null
      if (plan) {
        set((s) => ({
          planById: { ...s.planById, [plan.plan_record_id]: plan },
          error: null,
          detailLoading: false,
        }))
      } else {
        const errorText = data && 'error' in data ? data.error : null
        set({ error: errorText, detailLoading: false })
      }
      return plan
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), detailLoading: false })
      return null
    }
  },

  fetchByConversation: async (conversationId: string) => {
    set({ detailLoading: true })
    try {
      // Backend returns the BARE plan dict or null (no envelope).
      const data = await fetchApi<PlanDetail | null>(
        `/objective-plan/by-conversation/${conversationId}`,
      )
      const plan = data && data.plan_record_id ? data : null
      if (plan) {
        set((s) => ({
          planById: { ...s.planById, [plan.plan_record_id]: plan },
          error: null,
          detailLoading: false,
        }))
      } else {
        set({ error: null, detailLoading: false })
      }
      return plan
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), detailLoading: false })
      return null
    }
  },

  fetchVersions: async (planRecordId: string) => {
    try {
      // Backend returns a BARE ascending array of version rows.
      const data = await fetchApi<PlanSummary[]>(`/objective-plan/${planRecordId}/versions`)
      const versions = Array.isArray(data) ? data : []
      // The versions endpoint is keyed by plan_record_id but returns every
      // version of that record's objective_id (ascending). Cache under the
      // objective_id so the version selector can key off the whole lineage.
      const objectiveId = versions[0]?.objective_id
      if (objectiveId) {
        set((s) => ({
          versionsByObjective: { ...s.versionsByObjective, [objectiveId]: versions },
          error: null,
        }))
      }
      return versions
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) })
      return []
    }
  },

  decide: async (
    planRecordId: string,
    decision: PlanDecision,
    reason: string | undefined,
    expectedVersion: number,
  ) => {
    set({ decidingPlanId: planRecordId })
    try {
      const result = await fetchApi<DecisionResponse>(
        `/objective-plan/${planRecordId}/decision`,
        {
          method: 'POST',
          body: JSON.stringify({
            decision,
            ...(reason ? { reason } : {}),
            expected_current_version: expectedVersion,
          }),
        },
      )
      // NEVER trust the POST's echoed body as truth on its own — re-read the
      // canonical record so the surface, detail, and versions all reflect the
      // server's governed post-decision state.
      const fresh = await get().fetchPlan(planRecordId)
      await get().fetchSurface()
      set({ decidingPlanId: null, error: result.error ?? null })
      return {
        ok: result.ok,
        plan: fresh ?? result.plan,
        error: result.error ?? null,
        conflict: result.conflict,
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      // A 409 version-conflict surfaces through fetchApi as an ApiError; re-read
      // truth so the operator sees the current server version, then report it.
      await get().fetchPlan(planRecordId).catch(() => null)
      set({ decidingPlanId: null, error: message })
      return { ok: false, error: message, conflict: /conflict|409|version/i.test(message) }
    }
  },
}))
