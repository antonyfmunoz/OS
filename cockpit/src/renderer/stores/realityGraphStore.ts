import { create } from 'zustand'

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

const API = '/api/umh'

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
      const res = await fetch(`${API}/reality-graph/summary`)
      if (res.ok) set({ summary: await res.json() })
    } catch { /* ignore */ }
    set({ loading: false })
  },

  fetchEntities: async (entityType?: string) => {
    set({ loading: true })
    try {
      const url = entityType
        ? `${API}/reality-graph/entities?entity_type=${entityType}`
        : `${API}/reality-graph/entities`
      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        set({ entities: data.entities || [] })
      }
    } catch { /* ignore */ }
    set({ loading: false })
  },

  fetchEntity: async (entityId: string) => {
    set({ loading: true })
    try {
      const res = await fetch(`${API}/reality-graph/entity/${entityId}`)
      if (res.ok) set({ selectedEntity: await res.json() })
    } catch { /* ignore */ }
    set({ loading: false })
  },

  fetchNeighbors: async (entityId: string) => {
    try {
      const res = await fetch(`${API}/reality-graph/neighbors/${entityId}`)
      if (res.ok) {
        const data = await res.json()
        set({ neighbors: data.neighbors || [] })
      }
    } catch { /* ignore */ }
  },

  resolveContext: async (text: string) => {
    set({ loading: true })
    try {
      const res = await fetch(`${API}/context-resolution/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (res.ok) set({ resolvedContext: await res.json() })
    } catch { /* ignore */ }
    set({ loading: false })
  },

  searchEntities: async (q: string) => {
    set({ loading: true })
    try {
      const res = await fetch(`${API}/reality-graph/search?q=${encodeURIComponent(q)}`)
      if (res.ok) {
        const data = await res.json()
        set({ entities: data.results || [] })
      }
    } catch { /* ignore */ }
    set({ loading: false })
  },

  fetchArtifacts: async (type?: string) => {
    try {
      const url = type
        ? `${API}/artifact-registry/artifacts?artifact_type=${type}`
        : `${API}/artifact-registry/artifacts`
      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        set({ artifacts: data.artifacts || [] })
      }
    } catch { /* ignore */ }
  },

  fetchRepoSnapshot: async () => {
    try {
      const res = await fetch(`${API}/repository-awareness/snapshot`)
      if (res.ok) set({ repoSnapshot: await res.json() })
    } catch { /* ignore */ }
  },

  fetchDocsSnapshot: async () => {
    try {
      const res = await fetch(`${API}/documentation-awareness/snapshot`)
      if (res.ok) set({ docsSnapshot: await res.json() })
    } catch { /* ignore */ }
  },

  fetchRuntimeSnapshot: async () => {
    try {
      const res = await fetch(`${API}/runtime-awareness/snapshot`)
      if (res.ok) set({ runtimeSnapshot: await res.json() })
    } catch { /* ignore */ }
  },

  fetchKnowledgeSnapshot: async () => {
    try {
      const res = await fetch(`${API}/knowledge-awareness/snapshot`)
      if (res.ok) set({ knowledgeSnapshot: await res.json() })
    } catch { /* ignore */ }
  },
}))
