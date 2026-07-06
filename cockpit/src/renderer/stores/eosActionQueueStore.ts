// EOS action approval queue store — WP-P4-EOS-ACTION-QUEUE-COCKPIT-001.
//
// Client for the governed EOS action lifecycle seams (#183 read, #184
// approve/reject, #185 execute). The server is the ONLY authority: proposal
// status is never mutated locally — every decision/execution stores the
// server's response envelope (scrubbed) and then re-fetches the queue with a
// dedup-busting query param so the refetch cannot be coalesced into a poll
// request issued before the mutation landed. The actor identity is derived
// server-side from the authenticated operator principal — this client sends
// no decided_by/executed_by. No provider SDKs, no token material, no direct
// DB access.
import { create } from 'zustand'
import { fetchApi } from '../api/client'

export interface EOSActionProposal {
  proposal_id: string
  agent_id: string | null
  agent_name: string | null
  user_id: string | null
  action_type: string
  target_domain: string | null
  requested_operation: string | null
  summary: string | null
  status: string
  approval_state: string
  requires_approval: boolean
  priority: string | null
  retry_count: number | null
  max_retries: number | null
  created_at: string | null
  updated_at: string | null
  source: string
  beast_head: string | null
  umh_primitive: string
  execute_enabled: boolean
}

export interface EOSActionQueueEnvelope {
  projection_id: string
  surface: string
  connection_status: string
  source_build_safe: boolean
  execute_enabled: boolean
  executor_scope?: string
  allowed_action_types?: string
  retry_policy: string
  beast_head: string | null
  seam_id?: string
  proposal_count: number
  proposals: EOSActionProposal[]
  error: string | null
}

// Server response envelope for approve/reject (#184) and execute (#185).
export interface EOSActionResult {
  surface: string
  proposal_id: string
  decision?: string
  decided_by?: string
  decided_at?: string | null
  decision_applied?: boolean
  executed_by?: string
  executed_at?: string | null
  execution_applied?: boolean
  action_type?: string | null
  prior_status?: string | null
  new_status?: string | null
  result_ref?: string | null
  requeued_for_reapproval?: boolean
  retry_count?: number | null
  max_retries?: number | null
  retry_policy?: string
  envelope_id?: string
  governance_status?: string
  error?: string | null
}

// Defense-in-depth: the backend returns stable error codes (read seam) or
// scrubbed text (execution seam), but the UI never renders a server string
// without bounding it and redacting both URI-shaped DSNs and libpq
// keyword-style credentials itself.
const URI_PATTERN = /[a-z][a-z0-9+.-]*:\/\/\S+/gi
const KV_CREDENTIAL_PATTERN = /\b(password|passwd|pwd|secret|token|apikey|api_key)\s*=\s*\S+/gi

export function safeErrorText(value: unknown): string {
  const text = value instanceof Error ? value.message : String(value ?? '')
  return text
    .replace(URI_PATTERN, '<redacted-uri>')
    .replace(KV_CREDENTIAL_PATTERN, '<redacted-credential>')
    .slice(0, 300)
}

function safeField(value: string | null | undefined): string | null | undefined {
  return value == null ? value : safeErrorText(value)
}

function scrubResult(result: EOSActionResult): EOSActionResult {
  return {
    ...result,
    result_ref: safeField(result.result_ref),
    envelope_id: result.envelope_id ? safeErrorText(result.envelope_id) : result.envelope_id,
    governance_status: result.governance_status
      ? safeErrorText(result.governance_status)
      : result.governance_status,
    error: result.error ? safeErrorText(result.error) : result.error ?? null,
  }
}

interface EOSActionQueueState {
  connectionStatus: string
  sourceBuildSafe: boolean
  retryPolicy: string
  allowedActionTypes: string
  beastHead: string | null
  proposals: EOSActionProposal[]
  queueError: string | null
  loading: boolean
  busy: Record<string, boolean>
  results: Record<string, EOSActionResult>

  fetchProposals: (opts?: { fresh?: boolean }) => Promise<void>
  approve: (proposalId: string, reason?: string) => Promise<void>
  reject: (proposalId: string, reason?: string) => Promise<void>
  execute: (proposalId: string) => Promise<void>
}

// Monotonic counters: `fetchSeq` orders responses so a slow, stale GET can
// never overwrite a newer one; `freshSeq` cache-busts the post-mutation
// refetch past the api client's in-flight GET deduplication.
let fetchSeq = 0
let appliedSeq = 0
let freshSeq = 0

async function postAction(
  path: string,
  body: Record<string, unknown>,
): Promise<EOSActionResult> {
  try {
    return await fetchApi<EOSActionResult>(path, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  } catch (err) {
    return {
      surface: 'client_error',
      proposal_id: String(body.proposal_id ?? ''),
      error: safeErrorText(err),
    }
  }
}

export const useEOSActionQueueStore = create<EOSActionQueueState>((set, get) => ({
  connectionStatus: 'unknown',
  sourceBuildSafe: false,
  retryPolicy: '',
  allowedActionTypes: '',
  beastHead: null,
  proposals: [],
  queueError: null,
  loading: false,
  busy: {},
  results: {},

  fetchProposals: async (opts?: { fresh?: boolean }) => {
    const seq = ++fetchSeq
    const path = opts?.fresh
      ? `/eos/action-proposals?fresh=${++freshSeq}`
      : '/eos/action-proposals'
    set({ loading: true })
    try {
      const data = await fetchApi<EOSActionQueueEnvelope>(path)
      if (seq < appliedSeq) return // a newer response already landed
      appliedSeq = seq
      set({
        connectionStatus: data.connection_status,
        sourceBuildSafe: data.source_build_safe === true,
        retryPolicy: data.retry_policy ?? '',
        allowedActionTypes: data.allowed_action_types ?? '',
        beastHead: data.beast_head ?? null,
        proposals: Array.isArray(data.proposals) ? data.proposals : [],
        queueError: data.error ? safeErrorText(data.error) : null,
        loading: false,
      })
    } catch (err) {
      if (seq < appliedSeq) return
      appliedSeq = seq
      set({ queueError: safeErrorText(err), loading: false })
    }
  },

  approve: async (proposalId: string, reason?: string) => {
    set((s) => ({ busy: { ...s.busy, [proposalId]: true } }))
    const result = await postAction(
      `/eos/action-proposals/${proposalId}/approve`,
      { proposal_id: proposalId, ...(reason ? { reason } : {}) },
    )
    set((s) => ({
      results: { ...s.results, [proposalId]: scrubResult(result) },
      busy: { ...s.busy, [proposalId]: false },
    }))
    await get().fetchProposals({ fresh: true })
  },

  reject: async (proposalId: string, reason?: string) => {
    set((s) => ({ busy: { ...s.busy, [proposalId]: true } }))
    const result = await postAction(
      `/eos/action-proposals/${proposalId}/reject`,
      { proposal_id: proposalId, ...(reason ? { reason } : {}) },
    )
    set((s) => ({
      results: { ...s.results, [proposalId]: scrubResult(result) },
      busy: { ...s.busy, [proposalId]: false },
    }))
    await get().fetchProposals({ fresh: true })
  },

  execute: async (proposalId: string) => {
    set((s) => ({ busy: { ...s.busy, [proposalId]: true } }))
    const result = await postAction(
      `/eos/action-proposals/${proposalId}/execute`,
      { proposal_id: proposalId },
    )
    set((s) => ({
      results: { ...s.results, [proposalId]: scrubResult(result) },
      busy: { ...s.busy, [proposalId]: false },
    }))
    await get().fetchProposals({ fresh: true })
  },
}))
