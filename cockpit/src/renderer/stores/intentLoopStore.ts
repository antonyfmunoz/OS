// Intent-loop store — P4S-31 read surface + P4S-31B downstream decision.
//
// DOCTRINE: intent originates ONLY through sanctioned Cockpit conversational
// surfaces (Cockpit Chat now; Cockpit Voice later, into the same Chat
// channel). This store deliberately has NO submit action — intent capture
// happens in the server-side chat rail (deterministic classify_intent →
// governed intent_loop_submit). The store is a downstream control client:
// - GET  /api/umh/intent-loop                    (read surface — P4S-31)
// - POST /api/umh/intent-loop/{loop_id}/decision (approve/reject — P4S-31B)
// backed by transports/api/cockpit_intent_loop_routes.py +
// substrate.execution.intent.loop. The decision goes through the SERVER's
// governed runtime (registered MutationSpec); the store never advances the
// gate client-side — it re-reads server truth after every write. Same authed
// fetch pattern as the existing read poll.
import { create } from 'zustand'
import { fetchApi } from '../api/client'

export interface IntentLoopSpec {
  intent_id: string
  raw_text: string
  intent_type: string
  route_type: string
  risk_level: string
  confidence: number
  reasoning: string
  stage: string
  deterministic: boolean
}

export interface IntentLoopDraft {
  draft_id: string
  intent_id: string
  description: string
  status: string
  priority: string
  risk_level: string
  actionable: boolean
}

export interface IntentLoopProof {
  proof_id: string
  intent_id: string
  draft_id: string
  decision: string
  decided_by: string
  mutation_name: string
  envelope_id: string
  governance_status: string
  governed_success: boolean
  degraded: boolean
  resulting_stage: string
  reason?: string | null
  error?: string | null
}

export interface IntentLoopRecord {
  loop_id: string
  stage: string
  spec: IntentLoopSpec
  draft: IntentLoopDraft
  proof?: IntentLoopProof | null
  created_at: number
  updated_at: number
}

export interface IntentLoopSurface {
  surface: string
  canonical_runtime?: string
  connection_status: string
  total: number
  awaiting_approval: number
  proof_recorded: number
  stage_counts: Record<string, number>
  loops: IntentLoopRecord[]
  error?: string | null
}

export interface IntentLoopDecisionResult {
  surface: string
  decided: boolean
  loop_id?: string
  stage?: string
  proof?: IntentLoopProof | null
  error?: string | null
}

interface IntentLoopState {
  surface: IntentLoopSurface | null
  loading: boolean
  error: string | null
  decidingLoopId: string | null
  fetchSurface: () => Promise<void>
  decideLoop: (loopId: string, decision: 'approve' | 'reject') => Promise<IntentLoopDecisionResult>
}

export const useIntentLoopStore = create<IntentLoopState>((set, get) => ({
  surface: null,
  loading: false,
  error: null,
  decidingLoopId: null,

  fetchSurface: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<IntentLoopSurface>('/intent-loop')
      set({ surface: data, error: data.error ?? null, loading: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false })
    }
  },

  decideLoop: async (loopId: string, decision: 'approve' | 'reject') => {
    set({ decidingLoopId: loopId })
    try {
      const result = await fetchApi<IntentLoopDecisionResult>(
        `/intent-loop/${loopId}/decision`,
        { method: 'POST', body: JSON.stringify({ decision }) },
      )
      await get().fetchSurface()
      set({ decidingLoopId: null, error: result.error ?? null })
      return result
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      set({ decidingLoopId: null, error: message })
      return { surface: 'intent_loop_decision', decided: false, loop_id: loopId, error: message }
    }
  },
}))
