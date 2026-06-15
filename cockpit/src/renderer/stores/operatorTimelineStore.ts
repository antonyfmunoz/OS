import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface TimelineEntry {
  entry_id: string
  entry_type: 'intent_receipt' | 'event' | 'governance' | 'work_packet' | 'memory_write'
  timestamp: number
  summary: string
  details: Record<string, unknown>
  intent_id: string | null
  correlation_id: string | null
}

interface OperatorTimelineState {
  entries: TimelineEntry[]
  loading: boolean
  error: string | null
  selectedIntentId: string | null

  fetchTimeline: (limit?: number) => Promise<void>
  selectIntent: (intentId: string | null) => void
}

export const useOperatorTimelineStore = create<OperatorTimelineState>((set) => ({
  entries: [],
  loading: false,
  error: null,
  selectedIntentId: null,

  fetchTimeline: async (limit = 50) => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<{ timeline: TimelineEntry[]; total: number }>(
        `/operator/timeline?limit=${limit}`,
      )
      set({ entries: data.timeline, loading: false })
    } catch {
      set({ error: 'Failed to fetch timeline', loading: false })
    }
  },

  selectIntent: (intentId) => set({ selectedIntentId: intentId }),
}))
