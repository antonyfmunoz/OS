import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface ProjectionIntegrationState {
  snapshot: Record<string, unknown> | null
  profiles: Record<string, unknown>[]
  locations: Record<string, unknown>[]
  gaps: Record<string, unknown>[]
  readiness: Record<string, unknown> | null
  loading: boolean
  fetchSnapshot: () => Promise<void>
  fetchProfile: (id: string) => Promise<void>
  fetchLocations: (id: string) => Promise<void>
  fetchGaps: (id: string) => Promise<void>
  fetchReadiness: (id: string) => Promise<void>
  auditProjection: (id: string) => Promise<void>
}

export const useProjectionIntegrationStore = create<ProjectionIntegrationState>((set) => ({
  snapshot: null,
  profiles: [],
  locations: [],
  gaps: [],
  readiness: null,
  loading: false,

  fetchSnapshot: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>>('/projections/integration/snapshot')
      set({ snapshot: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchProfile: async (id: string) => {
    try {
      const data = await fetchApi<Record<string, unknown>>(`/projections/integration/profile/${id}`)
      set((s) => ({
        profiles: [...s.profiles.filter((p) => (p as { projection_id?: string }).projection_id !== id), data],
      }))
    } catch { /* noop */ }
  },

  fetchLocations: async (id: string) => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>(`/projections/integration/locations/${id}`)
      set({ locations: data })
    } catch {
      set({ locations: [] })
    }
  },

  fetchGaps: async (id: string) => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>(`/projections/integration/gaps/${id}`)
      set({ gaps: data })
    } catch {
      set({ gaps: [] })
    }
  },

  fetchReadiness: async (id: string) => {
    try {
      const data = await fetchApi<Record<string, unknown>>(`/projections/integration/readiness/${id}`)
      set({ readiness: data })
    } catch {
      set({ readiness: null })
    }
  },

  auditProjection: async (id: string) => {
    try {
      await fetchApi(`/projections/integration/audit/${id}`, { method: 'POST' })
    } catch { /* noop */ }
  },
}))
