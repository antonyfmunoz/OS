import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface WorkstationSessionState {
  activeSession: Record<string, unknown> | null
  history: Record<string, unknown>[]
  lastCheckpoint: Record<string, unknown> | null
  loading: boolean

  fetchActiveSession: () => Promise<void>
  fetchHistory: (limit?: number) => Promise<void>
  fetchLastCheckpoint: (sessionId: string) => Promise<void>
  startSession: () => Promise<void>
  checkpoint: (sessionId: string) => Promise<void>
  pause: (sessionId: string) => Promise<void>
  resumeSession: (sessionId: string) => Promise<void>
  close: (sessionId: string) => Promise<void>
}

export const useWorkstationSessionStore = create<WorkstationSessionState>((set, get) => ({
  activeSession: null,
  history: [],
  lastCheckpoint: null,
  loading: false,

  fetchActiveSession: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>>('/wk-session/active')
      set({ activeSession: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchHistory: async (limit = 20) => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>(`/wk-session/history?limit=${limit}`)
      set({ history: data })
    } catch {
      set({ history: [] })
    }
  },

  fetchLastCheckpoint: async (sessionId: string) => {
    try {
      const data = await fetchApi<Record<string, unknown>>(`/wk-session/${sessionId}/checkpoint`)
      set({ lastCheckpoint: data })
    } catch {
      set({ lastCheckpoint: null })
    }
  },

  startSession: async () => {
    await fetchApi('/wk-session/start', { method: 'POST' }).catch(() => {})
    get().fetchActiveSession()
  },

  checkpoint: async (sessionId: string) => {
    await fetchApi(`/wk-session/${sessionId}/checkpoint`, { method: 'POST' }).catch(() => {})
    get().fetchActiveSession()
  },

  pause: async (sessionId: string) => {
    await fetchApi(`/wk-session/${sessionId}/pause`, { method: 'POST' }).catch(() => {})
    get().fetchActiveSession()
  },

  resumeSession: async (sessionId: string) => {
    await fetchApi(`/wk-session/${sessionId}/resume`, { method: 'POST' }).catch(() => {})
    get().fetchActiveSession()
  },

  close: async (sessionId: string) => {
    await fetchApi(`/wk-session/${sessionId}/close`, { method: 'POST' }).catch(() => {})
    get().fetchActiveSession()
  },
}))
