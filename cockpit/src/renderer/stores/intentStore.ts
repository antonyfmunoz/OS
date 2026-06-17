import { create } from 'zustand'
import { fetchApi } from '../api/client'

export interface CanonicalIntent {
  intent_id: string
  scope: string
  statement: string
  rationale: string
  success_criteria: string[]
  created_at: number
  version: number
  parent_id: string
  status: string
  superseded_by: string
  evidence: string[]
}

export interface IntentConflict {
  conflict_id: string
  intent_a_id: string
  intent_b_id: string
  conflict_type: string
  description: string
  resolution: string
}

interface IntentState {
  activeIntents: CanonicalIntent[]
  summary: Record<string, unknown> | null
  conflicts: IntentConflict[]
  loading: boolean
  error: string | null
  fetchActive: () => Promise<void>
  fetchSummary: () => Promise<void>
  fetchConflicts: () => Promise<void>
  captureIntent: (scope: string, statement: string, rationale?: string) => Promise<CanonicalIntent | null>
}

export const useIntentStore = create<IntentState>((set) => ({
  activeIntents: [],
  summary: null,
  conflicts: [],
  loading: false,
  error: null,

  fetchActive: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi('/api/umh/intent/active')
      set({ activeIntents: data.intents ?? [], loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  fetchSummary: async () => {
    try {
      const data = await fetchApi('/api/umh/intent/summary')
      set({ summary: data.summary ?? null })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchConflicts: async () => {
    try {
      const data = await fetchApi('/api/umh/intent/conflicts')
      set({ conflicts: data.conflicts ?? [] })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  captureIntent: async (scope: string, statement: string, rationale?: string) => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi('/api/umh/intent/capture', {
        method: 'POST',
        body: JSON.stringify({ scope, statement, rationale: rationale ?? '' }),
      })
      set({ loading: false })
      return (data.intent as CanonicalIntent) ?? null
    } catch (e) {
      set({ error: String(e), loading: false })
      return null
    }
  },
}))
