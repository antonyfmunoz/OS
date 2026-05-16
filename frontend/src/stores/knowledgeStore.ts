import { create } from 'zustand'
import { fetchApi } from '../api/client'

export interface MemoryEntry {
  memory_id: string
  memory_type: string
  primitive_type: string
  label: string
  content: string
  confidence: number
  source_document_id?: string
  timestamp?: string
  authority_tier?: string | number
  domain_id?: string
  [key: string]: unknown
}

interface KnowledgeStats {
  total: number
  by_type: Record<string, number>
  by_tier: Record<string, number>
  by_domain: Record<string, number>
}

interface KnowledgeState {
  entries: MemoryEntry[]
  stats: KnowledgeStats | null
  total: number
  isLoading: boolean
  searchQuery: string
  selectedEntry: MemoryEntry | null
  fetchEntries: (limit?: number, offset?: number) => Promise<void>
  fetchStats: () => Promise<void>
  search: (q: string) => Promise<void>
  selectEntry: (entry: MemoryEntry | null) => void
}

export const useKnowledgeStore = create<KnowledgeState>((set) => ({
  entries: [],
  stats: null,
  total: 0,
  isLoading: false,
  searchQuery: '',
  selectedEntry: null,

  fetchEntries: async (limit = 50, offset = 0) => {
    set({ isLoading: true })
    try {
      const data = await fetchApi<{
        entries: MemoryEntry[]
        total: number
      }>(`/api/knowledge/entries?limit=${limit}&offset=${offset}`)
      set({ entries: data.entries, total: data.total, isLoading: false })
    } catch {
      set({ isLoading: false })
    }
  },

  fetchStats: async () => {
    try {
      const stats = await fetchApi<KnowledgeStats>('/api/knowledge/stats')
      set({ stats })
    } catch {
      // Stats fetch failed — leave null
    }
  },

  search: async (q: string) => {
    set({ isLoading: true, searchQuery: q })
    if (!q) {
      const data = await fetchApi<{ entries: MemoryEntry[]; total: number }>(
        '/api/knowledge/entries?limit=50&offset=0'
      )
      set({ entries: data.entries, total: data.total, isLoading: false })
      return
    }
    try {
      const data = await fetchApi<{
        results: MemoryEntry[]
        count: number
      }>(`/api/knowledge/search?q=${encodeURIComponent(q)}`)
      set({ entries: data.results, total: data.count, isLoading: false })
    } catch {
      set({ isLoading: false })
    }
  },

  selectEntry: (entry) => set({ selectedEntry: entry }),
}))
