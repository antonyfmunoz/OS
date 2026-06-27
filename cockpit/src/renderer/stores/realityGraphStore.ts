import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface RealityEntity {
  entity_id: string
  entity_type: string
  name: string
  status: string
  properties: Record<string, unknown>
  source_system: string
  source_id: string
  last_observed: number
}

interface GraphSummary {
  entity_count: number
  relation_count: number
  entities_by_type: Record<string, number>
  relations_by_type: Record<string, number>
  built_at: number
}

interface ResolvedContext {
  project_id: string
  project_name: string
  repository_id: string
  repository_name: string
  workspace_id: string
  workspace_name: string
  device_id: string
  active_device: string
  projection: string
  documents: Array<Record<string, unknown>>
  infrastructure: Array<Record<string, unknown>>
  files: Array<Record<string, unknown>>
  decisions: Array<Record<string, unknown>>
  active_work: Array<Record<string, unknown>>
  approvals: Array<Record<string, unknown>>
  constraints: Array<Record<string, unknown>>
  knowledge: Array<Record<string, unknown>>
  unresolved_references: string[]
  resolution_chain: Array<Record<string, string>>
  confidence: number
  strategy: string
  resolved_at: number
}

interface ArtifactEntry {
  artifact_id: string
  artifact_type: string
  name: string
  source_path: string
  status: string
  entity_refs: string[]
  created_at: number
}

interface RepositorySnapshot {
  repository_id: string
  name: string
  root_path: string
  branch: string
  file_count: number
  files_by_category: Record<string, number>
  important_files: Array<Record<string, unknown>>
  detected_at: number
}

interface DocumentationSnapshot {
  total_docs: number
  by_status: Record<string, number>
  by_source_type: Record<string, number>
  stale_docs: Array<Record<string, unknown>>
  detected_at: number
}

interface RuntimeAwarenessSnapshot {
  worktrees: Array<Record<string, unknown>>
  repositories: Array<Record<string, unknown>>
  processes: Array<Record<string, unknown>>
  containers: Array<Record<string, unknown>>
  active_executions: Array<Record<string, unknown>>
  active_work_packets: Array<Record<string, unknown>>
  blocked_work: Array<Record<string, unknown>>
  detected_at: number
}

interface KnowledgeSnapshot {
  total: number
  by_type: Record<string, number>
  recent: Array<Record<string, unknown>>
  detected_at: number
}

interface RealityGraphState {
  summary: GraphSummary | null
  entities: RealityEntity[]
  selectedEntity: RealityEntity | null
  neighbors: RealityEntity[]
  resolvedContext: ResolvedContext | null
  artifacts: ArtifactEntry[]
  repoSnapshot: RepositorySnapshot | null
  docsSnapshot: DocumentationSnapshot | null
  runtimeSnapshot: RuntimeAwarenessSnapshot | null
  knowledgeSnapshot: KnowledgeSnapshot | null
  loading: boolean
  fetchSummary: () => Promise<void>
  fetchEntities: (entityType?: string) => Promise<void>
  fetchEntity: (entityId: string) => Promise<void>
  fetchNeighbors: (entityId: string) => Promise<void>
  resolveContext: (text: string) => Promise<void>
  searchEntities: (q: string) => Promise<void>
  fetchArtifacts: (type?: string) => Promise<void>
  fetchRepoSnapshot: () => Promise<void>
  fetchDocsSnapshot: () => Promise<void>
  fetchRuntimeSnapshot: () => Promise<void>
  fetchKnowledgeSnapshot: () => Promise<void>
}

export const useRealityGraphStore = create<RealityGraphState>((set) => ({
  summary: null,
  entities: [],
  selectedEntity: null,
  neighbors: [],
  resolvedContext: null,
  artifacts: [],
  repoSnapshot: null,
  docsSnapshot: null,
  runtimeSnapshot: null,
  knowledgeSnapshot: null,
  loading: false,

  fetchSummary: async () => {
    set({ loading: true })
    try {
      const data = await fetchApi<GraphSummary>('/reality-graph/summary')
      set({ summary: data })
    } catch (e) {
      console.debug('fetchSummary failed:', e)
    }
    set({ loading: false })
  },

  fetchEntities: async (entityType?: string) => {
    set({ loading: true })
    try {
      const path = entityType
        ? `/reality-graph/entities?entity_type=${entityType}`
        : '/reality-graph/entities'
      const data = await fetchApi<{ entities: RealityEntity[] }>(path)
      set({ entities: data.entities || [] })
    } catch (e) {
      console.debug('fetchEntities failed:', e)
    }
    set({ loading: false })
  },

  fetchEntity: async (entityId: string) => {
    set({ loading: true })
    try {
      const data = await fetchApi<RealityEntity>(`/reality-graph/entity/${entityId}`)
      set({ selectedEntity: data })
    } catch (e) {
      console.debug('fetchEntity failed:', e)
    }
    set({ loading: false })
  },

  fetchNeighbors: async (entityId: string) => {
    try {
      const data = await fetchApi<{ neighbors: RealityEntity[] }>(`/reality-graph/neighbors/${entityId}`)
      set({ neighbors: data.neighbors || [] })
    } catch (e) {
      console.debug('fetchNeighbors failed:', e)
    }
  },

  resolveContext: async (text: string) => {
    set({ loading: true })
    try {
      const data = await fetchApi<ResolvedContext>('/context-resolution/resolve', {
        method: 'POST',
        body: JSON.stringify({ text }),
      })
      set({ resolvedContext: data })
    } catch (e) {
      console.debug('resolveContext failed:', e)
    }
    set({ loading: false })
  },

  searchEntities: async (q: string) => {
    set({ loading: true })
    try {
      const data = await fetchApi<{ results: RealityEntity[] }>(`/reality-graph/search?q=${encodeURIComponent(q)}`)
      set({ entities: data.results || [] })
    } catch (e) {
      console.debug('searchEntities failed:', e)
    }
    set({ loading: false })
  },

  fetchArtifacts: async (type?: string) => {
    try {
      const path = type
        ? `/artifact-registry/artifacts?artifact_type=${type}`
        : '/artifact-registry/artifacts'
      const data = await fetchApi<{ artifacts: ArtifactEntry[] }>(path)
      set({ artifacts: data.artifacts || [] })
    } catch (e) {
      console.debug('fetchArtifacts failed:', e)
    }
  },

  fetchRepoSnapshot: async () => {
    try {
      const data = await fetchApi<RepositorySnapshot>('/repository-awareness/snapshot')
      set({ repoSnapshot: data })
    } catch (e) {
      console.debug('fetchRepoSnapshot failed:', e)
    }
  },

  fetchDocsSnapshot: async () => {
    try {
      const data = await fetchApi<DocumentationSnapshot>('/documentation-awareness/snapshot')
      set({ docsSnapshot: data })
    } catch (e) {
      console.debug('fetchDocsSnapshot failed:', e)
    }
  },

  fetchRuntimeSnapshot: async () => {
    try {
      const data = await fetchApi<RuntimeAwarenessSnapshot>('/runtime-awareness/snapshot')
      set({ runtimeSnapshot: data })
    } catch (e) {
      console.debug('fetchRuntimeSnapshot failed:', e)
    }
  },

  fetchKnowledgeSnapshot: async () => {
    try {
      const data = await fetchApi<KnowledgeSnapshot>('/knowledge-awareness/snapshot')
      set({ knowledgeSnapshot: data })
    } catch (e) {
      console.debug('fetchKnowledgeSnapshot failed:', e)
    }
  },
}))
