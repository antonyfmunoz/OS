import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface RepositoryHealth {
  status: string
  dirty_file_count: number
  stale_branch_count: number
  detached_worktrees: number
  issues: string[]
}

interface Branch {
  name: string
  last_commit: string
  message: string
  timestamp: number
  ahead: number
  behind: number
  is_current: boolean
}

interface Worktree {
  path: string
  branch: string
  commit: string
  locked: boolean
  detached: boolean
}

interface Repository {
  repo_name: string
  repo_path: string
  current_branch: string
  head_commit: string
  head_commit_message: string
  head_commit_timestamp: number
  dirty_files: string[]
  staged_files: string[]
  worktree_count: number
  health: RepositoryHealth
  branches: Branch[]
  worktrees: Worktree[]
  snapshot_at: number
}

interface RiskItem {
  id: string
  level: string
  category: string
  description: string
  repo_path: string
}

interface Phase {
  phase_number: string
  phase_name: string
  state: string
  completed_at: string
  description: string
  key_files: string[]
  blockers: string[]
}

interface RoadmapData {
  current_phase: Phase | null
  completed_phases: Phase[]
  planned_phases: Phase[]
  blocked_phases: Phase[]
  total_phases: number
  completion_ratio: number
  sources_checked: string[]
  generated_at: number
}

interface WorkspaceData {
  repo_count: number
  repos: Array<{
    name: string
    path: string
    branch: string
    dirty: number
    staged: number
    branches: number
    worktrees: number
    health: string
    issues: string[]
  }>
  totals: {
    dirty_files: number
    staged_files: number
    branches: number
    worktrees: number
    stale_branches: number
    detached_worktrees: number
  }
  risks: RiskItem[]
  overall_risk: string
  generated_at: number
}

type ActiveTab = 'repositories' | 'workspace' | 'roadmap' | 'risks'

interface MetaIDEState {
  activeTab: ActiveTab
  repositories: Repository[]
  workspace: WorkspaceData | null
  roadmap: RoadmapData | null
  risks: RiskItem[]
  overallRisk: string
  loading: boolean
  error: string | null

  setActiveTab: (tab: ActiveTab) => void
  fetchRepositories: () => Promise<void>
  fetchWorkspace: () => Promise<void>
  fetchRoadmap: () => Promise<void>
  fetchRisks: () => Promise<void>
}

export const useMetaIDEStore = create<MetaIDEState>((set) => ({
  activeTab: 'workspace',
  repositories: [],
  workspace: null,
  roadmap: null,
  risks: [],
  overallRisk: 'none',
  loading: false,
  error: null,

  setActiveTab: (tab) => set({ activeTab: tab }),

  fetchRepositories: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<{ repositories: Repository[]; generated_at: number }>(
        '/api/umh/meta-ide/repositories',
      )
      set({ repositories: data.repositories, loading: false })
    } catch (err) {
      set({ error: String(err), loading: false })
    }
  },

  fetchWorkspace: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<WorkspaceData>('/api/umh/meta-ide/workspace')
      set({ workspace: data, loading: false })
    } catch (err) {
      set({ error: String(err), loading: false })
    }
  },

  fetchRoadmap: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<RoadmapData>('/api/umh/meta-ide/roadmap')
      set({ roadmap: data, loading: false })
    } catch (err) {
      set({ error: String(err), loading: false })
    }
  },

  fetchRisks: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<{ risks: RiskItem[]; overall_risk: string }>(
        '/api/umh/meta-ide/risks',
      )
      set({ risks: data.risks, overallRisk: data.overall_risk, loading: false })
    } catch (err) {
      set({ error: String(err), loading: false })
    }
  },
}))
