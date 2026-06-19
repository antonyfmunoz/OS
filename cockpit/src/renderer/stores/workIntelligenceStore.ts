import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface WorkIntelligenceState {
  overview: Record<string, unknown> | null
  readyWork: Record<string, unknown>[]
  blockedWork: Record<string, unknown>[]
  delegation: Record<string, unknown> | null
  drift: Record<string, unknown>[]
  velocity: Record<string, unknown> | null
  health: Record<string, unknown> | null
  loading: boolean
  fetchOverview: () => Promise<void>
  fetchReady: () => Promise<void>
  fetchBlocked: () => Promise<void>
  fetchDelegation: () => Promise<void>
  fetchDrift: () => Promise<void>
  fetchVelocity: () => Promise<void>
  fetchHealth: () => Promise<void>
  fetchAll: () => Promise<void>
}

export const useWorkIntelligenceStore = create<WorkIntelligenceState>((set) => ({
  overview: null,
  readyWork: [],
  blockedWork: [],
  delegation: null,
  drift: [],
  velocity: null,
  health: null,
  loading: false,

  fetchOverview: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>>('/work-intelligence/overview')
      set({ overview: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchReady: async () => {
    try {
      const data = await fetchApi<{ ready: Record<string, unknown>[] }>('/work-intelligence/ready')
      set({ readyWork: data.ready || [] })
    } catch {
      set({ readyWork: [] })
    }
  },

  fetchBlocked: async () => {
    try {
      const data = await fetchApi<{ blocked: Record<string, unknown>[] }>('/work-intelligence/blocked')
      set({ blockedWork: data.blocked || [] })
    } catch {
      set({ blockedWork: [] })
    }
  },

  fetchDelegation: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/work-intelligence/delegation')
      set({ delegation: data })
    } catch {
      set({ delegation: null })
    }
  },

  fetchDrift: async () => {
    try {
      const data = await fetchApi<{ drift: Record<string, unknown>[] }>('/work-intelligence/drift')
      set({ drift: data.drift || [] })
    } catch {
      set({ drift: [] })
    }
  },

  fetchVelocity: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/work-intelligence/velocity')
      set({ velocity: data })
    } catch {
      set({ velocity: null })
    }
  },

  fetchHealth: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/work-intelligence/health')
      set({ health: data })
    } catch {
      set({ health: null })
    }
  },

  fetchAll: async () => {
    set({ loading: true })
    try {
      const [overview, ready, blocked, delegation, drift, velocity, health] = await Promise.all([
        fetchApi<Record<string, unknown>>('/work-intelligence/overview').catch(() => null),
        fetchApi<{ ready: Record<string, unknown>[] }>('/work-intelligence/ready').catch(() => ({ ready: [] })),
        fetchApi<{ blocked: Record<string, unknown>[] }>('/work-intelligence/blocked').catch(() => ({ blocked: [] })),
        fetchApi<Record<string, unknown>>('/work-intelligence/delegation').catch(() => null),
        fetchApi<{ drift: Record<string, unknown>[] }>('/work-intelligence/drift').catch(() => ({ drift: [] })),
        fetchApi<Record<string, unknown>>('/work-intelligence/velocity').catch(() => null),
        fetchApi<Record<string, unknown>>('/work-intelligence/health').catch(() => null),
      ])
      set({
        overview,
        readyWork: ready?.ready || [],
        blockedWork: blocked?.blocked || [],
        delegation,
        drift: drift?.drift || [],
        velocity,
        health,
        loading: false,
      })
    } catch {
      set({ loading: false })
    }
  },
}))
