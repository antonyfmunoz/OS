import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface DelegationState {
  summary: Record<string, unknown> | null
  proposals: Record<string, unknown>[]
  missions: Record<string, unknown>[]
  activeMissions: Record<string, unknown>[]
  selectedMission: Record<string, unknown> | null
  loading: boolean

  fetchSummary: () => Promise<void>
  fetchProposals: (status?: string) => Promise<void>
  fetchMissions: (status?: string) => Promise<void>
  fetchActiveMissions: () => Promise<void>
  getMission: (id: string) => Promise<void>
  propose: (intent: string, clarifiedIntent?: string) => Promise<void>
  approveProposal: (id: string) => Promise<void>
  rejectProposal: (id: string, reason?: string) => Promise<void>
  approveWorkPacket: (missionId: string) => Promise<void>
  cancelMission: (missionId: string) => Promise<void>
}

export const useDelegationStore = create<DelegationState>((set, get) => ({
  summary: null,
  proposals: [],
  missions: [],
  activeMissions: [],
  selectedMission: null,
  loading: false,

  fetchSummary: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>>('/delegation/summary')
      set({ summary: data, loading: false })
    } catch {
      set({ summary: null, loading: false })
    }
  },

  fetchProposals: async (status?: string) => {
    try {
      const path = status ? `/delegation/proposals?status=${status}` : '/delegation/proposals'
      const data = await fetchApi<Record<string, unknown>[]>(path)
      set({ proposals: data })
    } catch {
      set({ proposals: [] })
    }
  },

  fetchMissions: async (status?: string) => {
    try {
      const path = status ? `/delegation/missions?status=${status}` : '/delegation/missions'
      const data = await fetchApi<Record<string, unknown>[]>(path)
      set({ missions: data })
    } catch {
      set({ missions: [] })
    }
  },

  fetchActiveMissions: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>('/delegation/missions/active')
      set({ activeMissions: data })
    } catch {
      set({ activeMissions: [] })
    }
  },

  getMission: async (id: string) => {
    try {
      const data = await fetchApi<Record<string, unknown>>(`/delegation/missions/${id}`)
      set({ selectedMission: data })
    } catch {
      set({ selectedMission: null })
    }
  },

  propose: async (intent: string, clarifiedIntent?: string) => {
    try {
      await fetchApi('/delegation/propose', {
        method: 'POST',
        body: JSON.stringify({ intent, clarified_intent: clarifiedIntent }),
      })
      await get().fetchProposals()
    } catch {
      /* surfaced via empty proposals */
    }
  },

  approveProposal: async (id: string) => {
    try {
      await fetchApi(`/delegation/proposals/${id}/approve`, { method: 'POST' })
      await get().fetchProposals()
      await get().fetchMissions()
    } catch {
      /* refresh handles state */
    }
  },

  rejectProposal: async (id: string, reason?: string) => {
    try {
      await fetchApi(`/delegation/proposals/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      })
      await get().fetchProposals()
    } catch {
      /* refresh handles state */
    }
  },

  approveWorkPacket: async (missionId: string) => {
    try {
      await fetchApi(`/delegation/missions/${missionId}/approve-work-packet`, { method: 'POST' })
      await get().fetchMissions()
      await get().fetchActiveMissions()
    } catch {
      /* refresh handles state */
    }
  },

  cancelMission: async (missionId: string) => {
    try {
      await fetchApi(`/delegation/missions/${missionId}/cancel`, { method: 'POST' })
      await get().fetchMissions()
      await get().fetchActiveMissions()
    } catch {
      /* refresh handles state */
    }
  },
}))
