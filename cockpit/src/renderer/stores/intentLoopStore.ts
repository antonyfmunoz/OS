// Intent-loop mirror store — P4S-31.
//
// Thin read-only client for the substrate-owned MVP operating-loop read
// surface (GET /api/umh/intent-loop — transports/api/cockpit_intent_loop_routes
// .py, backed by substrate.execution.intent.loop::read_intent_loop_surface).
// MIRROR, NOT CONTROL: this store only reads and reflects that server-truth
// dict — it never submits or decides an intent (approval flows through the
// canonical governed_mutation runtime, not the cockpit). Same read-only polling
// shape as projectionMirrorStore.ts (P4S-30).
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

interface IntentLoopState {
  surface: IntentLoopSurface | null
  loading: boolean
  error: string | null
  fetchSurface: () => Promise<void>
}

export const useIntentLoopStore = create<IntentLoopState>((set) => ({
  surface: null,
  loading: false,
  error: null,

  fetchSurface: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<IntentLoopSurface>('/intent-loop')
      set({ surface: data, error: data.error ?? null, loading: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false })
    }
  },
}))
