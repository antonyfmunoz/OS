import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface Observation {
  id: string
  label: string
  description: string
  primitive_type: string
  evidence: string
  source_document: string
  relationships: { target: string; type: string }[]
  created_at: string
}

interface Skill {
  id: string
  name: string
  description: string
  trigger: 'scheduled' | 'conversational' | 'both'
  category: string
  usage_count: number
  last_used: string
  effort: string
}

interface MemoryEntry {
  id: string
  label: string
  description: string
  memory_type: string
  authority_tier: string
  source_document: string
  primitive_type: string
  created_at: string
  domain_id: string | null
}

interface TrackingEntry {
  id: string
  name: string
  entity_type: string
  last_changed: string
  change_count: number
  status: string
}

type ViewMode = 'observations' | 'memory' | 'skills' | 'tracking'

interface KnowledgeState {
  observations: Observation[]
  memory: MemoryEntry[]
  skills: Skill[]
  tracking: TrackingEntry[]
  viewMode: ViewMode
  searchQuery: string
  selectedNode: Observation | null
  setViewMode: (mode: ViewMode) => void
  setSearchQuery: (q: string) => void
  selectNode: (node: Observation | null) => void
  fetchObservations: () => Promise<void>
  fetchMemory: () => Promise<void>
  fetchSkills: () => Promise<void>
  fetchTracking: () => Promise<void>
}

export const useKnowledgeStore = create<KnowledgeState>((set) => ({
  observations: [],
  memory: [],
  skills: [],
  tracking: [],
  viewMode: 'observations',
  searchQuery: '',
  selectedNode: null,

  setViewMode: (mode) => set({ viewMode: mode }),
  setSearchQuery: (q) => set({ searchQuery: q }),
  selectNode: (node) => set({ selectedNode: node }),

  fetchObservations: async () => {
    try {
      const data = await fetchApi<Observation[]>('/observations')
      set({ observations: data })
    } catch { /* store stays stale */ }
  },

  fetchMemory: async () => {
    try {
      const data = await fetchApi<MemoryEntry[]>('/memory')
      set({ memory: data })
    } catch { /* store stays stale */ }
  },

  fetchSkills: async () => {
    try {
      const res = await fetchApi<{ skills: Skill[] } | Skill[]>('/skills')
      const data = Array.isArray(res) ? res : res.skills ?? []
      set({ skills: data })
    } catch { /* store stays stale */ }
  },

  fetchTracking: async () => {
    try {
      const data = await fetchApi<TrackingEntry[]>('/tracking')
      set({ tracking: data })
    } catch { /* store stays stale */ }
  },
}))
