import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface UnifiedWorkstationState {
  snapshot: Record<string, unknown> | null
  attention: { total: number; critical: number } | null
  loading: boolean

  fetchSnapshot: () => Promise<void>
  fetchAttention: () => Promise<void>
}

export const useUnifiedWorkstationStore = create<UnifiedWorkstationState>((set) => ({
  snapshot: null,
  attention: null,
  loading: false,

  fetchSnapshot: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/unified-workstation/snapshot')
      set({ snapshot: data })
    } catch {
      set({ snapshot: null })
    }
  },

  fetchAttention: async () => {
    try {
      const data = await fetchApi<{ total: number; critical: number }>('/attention/count')
      set({ attention: data })
    } catch {
      set({ attention: null })
    }
  },
}))
