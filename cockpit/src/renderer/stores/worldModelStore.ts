import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface WorldEntity {
  id: string
  name: string
  category: string
  status: string
  description: string
  evidence: Array<{ type: string; detail: string; observed_at: number }>
  capabilities: Array<{ name: string; provided_by: string; status: string }>
  depends_on: string[]
}

interface WorldGap {
  id: string
  description: string
  severity: string
  entity_id: string
  evidence: Array<{ type: string; detail: string }>
}

interface WorldUncertainty {
  id: string
  description: string
  entity_id: string
  reason: string
  confidence: number
}

interface WorldModelSummary {
  total_entities: number
  by_status: Record<string, number>
  by_category: Record<string, number>
  total_gaps: number
  gaps_by_severity: Record<string, number>
  total_uncertainties: number
  extracted_at: number
}

interface WorldModelData {
  summary: WorldModelSummary
  entities: Record<string, WorldEntity>
  gaps: WorldGap[]
  uncertainties: WorldUncertainty[]
  extracted_at: number
}

interface DependencyNode {
  id: string
  name: string
  category: string
  status: string
}

interface DependencyEdge {
  source: string
  target: string
  type: string
  strength: string
}

interface CriticalPath {
  path: string[]
  length: number
  risk: string
  description: string
}

interface DependencyGraphData {
  summary: {
    total_nodes: number
    total_edges: number
    edge_types: Record<string, number>
    orphaned: number
    cycles: number
    critical_path_length: number
    extracted_at: number
  }
  nodes: Record<string, DependencyNode>
  edges: DependencyEdge[]
  orphaned: string[]
  cycles: string[][]
  critical_paths: CriticalPath[]
  extracted_at: number
}

interface Contradiction {
  id: string
  type: string
  severity: string
  confidence: number
  recommended_fix: string
}

interface ContradictionData {
  summary: {
    total: number
    by_severity: Record<string, number>
    by_type: Record<string, number>
    checks_performed: number
    checked_at: number
  }
  contradictions: Contradiction[]
  checked_at: number
}

interface CompositionStep {
  id: string
  description: string
  action: string
  depends_on: string[]
  status: string
  risk_class: string
  governance_mode: string
  verification: string
}

interface CompositionPlan {
  summary: {
    plan_id: string
    intent: string
    total_steps: number
    step_status: Record<string, number>
    overall_risk: string
    governance_required: string
    missing_prerequisites: number
    risks: number
    created_at: number
  }
  steps: CompositionStep[]
  risks: Array<{ description: string; risk_class: string; mitigation: string }>
  evidence: string[]
  overall_risk: string
  governance_required: string
}

interface MemoryCandidate {
  id: string
  content: string
  category: string
  scope: string
  status: string
  confidence: number
  source_action: string
  created_at: number
}

interface MemoryPromotionData {
  summary: {
    total_candidates: number
    by_status: Record<string, number>
    canonical_entries: number
    pending_approvals: number
  }
  pending_approvals: MemoryCandidate[]
}

interface OutcomeRecord {
  id: string
  action_type: string
  plan_id: string
  step_id: string
  description: string
  status: string
  actual_result: string
  duration_seconds: number
  recorded_at: number
}

interface LearningLoopData {
  total_outcomes: number
  by_status: Record<string, number>
  reliability: Record<string, number>
  recent_outcomes: OutcomeRecord[]
  signals: Array<{ signal_type: string; description: string; generated_at: number }>
  promotion_candidates: string[]
}

type Tab = 'world' | 'graph' | 'contradictions' | 'compose' | 'outcomes' | 'memory'

interface WorldModelState {
  tab: Tab
  worldModel: WorldModelData | null
  depGraph: DependencyGraphData | null
  contradictions: ContradictionData | null
  plan: CompositionPlan | null
  learningLoop: LearningLoopData | null
  memoryPromotion: MemoryPromotionData | null
  composing: boolean
  loading: boolean
  error: string | null

  setTab: (tab: Tab) => void
  fetchWorldModel: () => Promise<void>
  fetchDepGraph: () => Promise<void>
  fetchContradictions: () => Promise<void>
  fetchLearningLoop: () => Promise<void>
  fetchMemoryPromotion: () => Promise<void>
  compose: (intent: string) => Promise<void>
  approveMemory: (id: string) => Promise<void>
  rejectMemory: (id: string, reason: string) => Promise<void>
  fetchAll: () => Promise<void>
}

export const useWorldModelStore = create<WorldModelState>((set, get) => ({
  tab: 'world',
  worldModel: null,
  depGraph: null,
  contradictions: null,
  plan: null,
  learningLoop: null,
  memoryPromotion: null,
  composing: false,
  loading: false,
  error: null,

  setTab: (tab) => set({ tab }),

  fetchWorldModel: async () => {
    try {
      const data = await fetchApi<WorldModelData>('/organism/world-model')
      set({ worldModel: data })
    } catch {
      set({ error: 'Failed to fetch world model' })
    }
  },

  fetchDepGraph: async () => {
    try {
      const data = await fetchApi<DependencyGraphData>('/organism/dependency-graph')
      set({ depGraph: data })
    } catch {
      set({ error: 'Failed to fetch dependency graph' })
    }
  },

  fetchContradictions: async () => {
    try {
      const data = await fetchApi<ContradictionData>('/organism/contradictions')
      set({ contradictions: data })
    } catch {
      set({ error: 'Failed to fetch contradictions' })
    }
  },

  fetchLearningLoop: async () => {
    try {
      const data = await fetchApi<LearningLoopData>('/organism/learning-loop')
      set({ learningLoop: data })
    } catch {
      set({ error: 'Failed to fetch learning loop' })
    }
  },

  fetchMemoryPromotion: async () => {
    try {
      const data = await fetchApi<MemoryPromotionData>('/organism/memory-promotion')
      set({ memoryPromotion: data })
    } catch {
      set({ error: 'Failed to fetch memory promotion' })
    }
  },

  compose: async (intent: string) => {
    set({ composing: true, error: null })
    try {
      const data = await fetchApi<CompositionPlan>('/organism/compose', {
        method: 'POST',
        body: JSON.stringify({ intent }),
      })
      set({ plan: data, composing: false, tab: 'compose' })
    } catch {
      set({ composing: false, error: 'Composition failed' })
    }
  },

  approveMemory: async (id: string) => {
    try {
      await fetchApi(`/organism/memory-promotion/${id}/approve`, { method: 'POST' })
      get().fetchMemoryPromotion()
    } catch {
      set({ error: 'Failed to approve memory' })
    }
  },

  rejectMemory: async (id: string, reason: string) => {
    try {
      await fetchApi(`/organism/memory-promotion/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      })
      get().fetchMemoryPromotion()
    } catch {
      set({ error: 'Failed to reject memory' })
    }
  },

  fetchAll: async () => {
    set({ loading: true })
    const s = get()
    await Promise.all([
      s.fetchWorldModel(),
      s.fetchDepGraph(),
      s.fetchContradictions(),
      s.fetchLearningLoop(),
      s.fetchMemoryPromotion(),
    ])
    set({ loading: false })
  },
}))
