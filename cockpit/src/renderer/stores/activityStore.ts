import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface ActivityEvent {
  id: string
  type: string
  source: string
  summary: string
  timestamp: string
  severity: 'info' | 'warning' | 'error'
  payload?: Record<string, unknown>
}

interface ActivityState {
  events: ActivityEvent[]
  filter: {
    source: string | null
    type: string | null
    severity: string | null
  }
  autoScroll: boolean

  fetchEvents: () => Promise<void>
  setFilter: (key: string, value: string | null) => void
  setAutoScroll: (on: boolean) => void
  addEvent: (event: ActivityEvent) => void
}

export const useActivityStore = create<ActivityState>((set) => ({
  events: [],
  filter: { source: null, type: null, severity: null },
  autoScroll: true,

  fetchEvents: async () => {
    try {
      const data = await fetchApi<ActivityEvent[]>('/api/umh/activity/stream?limit=200')
      set({ events: data })
    } catch {
      set({ events: [] })
    }
  },

  setFilter: (key, value) =>
    set((s) => ({ filter: { ...s.filter, [key]: value } })),

  setAutoScroll: (on) => set({ autoScroll: on }),

  addEvent: (event) =>
    set((s) => ({
      events: [...s.events.slice(-499), event],
    })),
}))
