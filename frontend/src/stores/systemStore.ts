import { create } from 'zustand'
import { fetchApi } from '../api/client'

export interface Container {
  ID: string
  Names: string
  Image: string
  Status: string
  Ports: string
  State: string
  [key: string]: unknown
}

interface SystemState {
  containers: Container[]
  costs: Record<string, unknown> | null
  costsAvailable: boolean
  ingestionStatus: { available: boolean; latest_proofs?: { name: string; path: string }[] }
  isLoading: boolean
  fetchContainers: () => Promise<void>
  fetchCosts: () => Promise<void>
  fetchIngestionStatus: () => Promise<void>
}

export const useSystemStore = create<SystemState>((set) => ({
  containers: [],
  costs: null,
  costsAvailable: false,
  ingestionStatus: { available: false },
  isLoading: false,

  fetchContainers: async () => {
    set({ isLoading: true })
    try {
      const data = await fetchApi<{ containers: Container[]; count: number }>(
        '/api/system/containers'
      )
      set({ containers: data.containers, isLoading: false })
    } catch {
      set({ isLoading: false })
    }
  },

  fetchCosts: async () => {
    try {
      const data = await fetchApi<{
        available: boolean
        data?: Record<string, unknown>
      }>('/api/system/costs')
      set({
        costs: data.data ?? null,
        costsAvailable: data.available,
      })
    } catch {
      // Cost fetch failed
    }
  },

  fetchIngestionStatus: async () => {
    try {
      const data = await fetchApi<{
        available: boolean
        latest_proofs?: { name: string; path: string }[]
      }>('/api/system/ingestion-status')
      set({ ingestionStatus: data })
    } catch {
      // Ingestion status fetch failed
    }
  },
}))
