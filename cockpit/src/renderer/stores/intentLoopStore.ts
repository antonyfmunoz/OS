// Intent-loop store — P4S-31 read surface + P4S-31B input surface.
//
// Client for the substrate-owned MVP operating loop:
// - GET  /api/umh/intent-loop                    (read surface — P4S-31)
// - POST /api/umh/intent-loop/submit             (operator submit — P4S-31B)
// - POST /api/umh/intent-loop/{loop_id}/decision (approve/reject — P4S-31B)
// backed by transports/api/cockpit_intent_loop_routes.py +
// substrate.execution.intent.loop. Writes go through the SERVER's governed
// runtime (every write routes through a registered MutationSpec on the server);
// this store only calls the authed routes and re-reads server truth. It never
// advances the gate client-side — the read surface remains the single source of
// truth. Same authed fetch pattern as the existing read poll.
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

export interface IntentLoopSubmitResult {
  surface: string
  submitted: boolean
  loop_id?: string
  stage?: string
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
  submitting: boolean
  decidingLoopId: string | null
  fetchSurface: () => Promise<void>
  submitIntent: (text: string) => Promise<IntentLoopSubmitResult>
  decideLoop: (loopId: string, decision: 'approve' | 'reject') => Promise<IntentLoopDecisionResult>
}

export const useIntentLoopStore = create<IntentLoopState>((set, get) => ({
  surface: null,
  loading: false,
  error: null,
  submitting: false,
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

  submitIntent: async (text: string) => {
    set({ submitting: true })
    try {
      const result = await fetchApi<IntentLoopSubmitResult>('/intent-loop/submit', {
        method: 'POST',
        body: JSON.stringify({ text }),
      })
      // Re-read server truth so the newly-held loop appears; the read surface,
      // not this call, is the source of truth for what is on the server.
      await get().fetchSurface()
      set({ submitting: false, error: result.error ?? null })
      return result
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      set({ submitting: false, error: message })
      return { surface: 'intent_loop_submit', submitted: false, error: message }
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
