import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface OperationsState {
  fabric: Record<string, unknown> | null
  workforce: Record<string, unknown> | null
  sessionMachine: Record<string, unknown> | null
  loading: boolean

  fetchFabric: () => Promise<void>
  fetchWorkforce: () => Promise<void>
  fetchSessionMachine: () => Promise<void>
  fetchAll: () => Promise<void>
}

export const useOperationsStore = create<OperationsState>((set) => ({
  fabric: null,
  workforce: null,
  sessionMachine: null,
  loading: false,

  fetchFabric: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/execution-fabric/snapshot')
      set({ fabric: data })
    } catch {
      set({ fabric: null })
    }
  },

  fetchWorkforce: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/agent-workforce/snapshot')
      set({ workforce: data })
    } catch {
      set({ workforce: null })
    }
  },

  fetchSessionMachine: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>>('/session-machine/snapshot')
      set({ sessionMachine: data })
    } catch {
      set({ sessionMachine: null })
    }
  },

  fetchAll: async () => {
    set({ loading: true })
    const store = useOperationsStore.getState()
    await Promise.all([
      store.fetchFabric(),
      store.fetchWorkforce(),
      store.fetchSessionMachine(),
    ])
    set({ loading: false })
  },
}))
