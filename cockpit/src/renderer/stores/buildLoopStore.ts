import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface BuildLoopState {
  status: Record<string, unknown> | null
  activeRequests: Record<string, unknown>[]
  history: Record<string, unknown>[]
  loading: boolean
  fetchStatus: () => Promise<void>
  fetchActive: () => Promise<void>
  fetchHistory: () => Promise<void>
  submit: (text: string, target?: string) => Promise<void>
}

export const useBuildLoopStore = create<BuildLoopState>((set, get) => ({
  status: null,
  activeRequests: [],
  history: [],
  loading: false,

  fetchStatus: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<Record<string, unknown>>('/build-loop/status')
      set({ status: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchActive: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>('/build-loop/active')
      set({ activeRequests: data })
    } catch {
      set({ activeRequests: [] })
    }
  },

  fetchHistory: async () => {
    try {
      const data = await fetchApi<Record<string, unknown>[]>('/build-loop/history')
      set({ history: data })
    } catch {
      set({ history: [] })
    }
  },

  submit: async (text: string, target?: string) => {
    try {
      await fetchApi('/build-loop/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, projection_target: target ?? '' }),
      })
      await get().fetchActive()
      await get().fetchStatus()
    } catch { /* noop */ }
  },
}))
