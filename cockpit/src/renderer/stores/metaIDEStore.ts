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

interface TerminalObs {
  terminal_id: string
  session_name: string
  window_name: string
  pane_index: number
  current_command: string
  cwd: string
  pid: number
  is_active: boolean
}

interface ContainerObs {
  container_id: string
  container_name: string
  image: string
  status: string
  health: string
  ports: string[]
  restart_count: number
}

interface PreviewObs {
  preview_id: string
  name: string
  port: number
  url: string
  process_name: string
  health: string
  restart_count: number
}

interface WorkspaceObservation {
  terminals: TerminalObs[]
  containers: ContainerObs[]
  previews: PreviewObs[]
  engineering_sessions: Array<Record<string, unknown>>
  repositories: Array<Record<string, unknown>>
  snapshot_id: string
}

type ActiveTab = 'files' | 'editor' | 'sessions' | 'repositories' | 'workspace' | 'roadmap' | 'risks' | 'terminals' | 'containers' | 'runtimes'
export type SidebarTab = 'files' | 'sessions' | 'workspace' | 'repositories' | 'roadmap' | 'risks'
export type PanelTab = 'terminal' | 'terminals' | 'containers' | 'runtimes'

export interface FileEntry { name: string; path: string; type: 'file' | 'directory' }
export interface FileMeshNode { id: string; name: string; os: string; status: string; ip?: string; device_type?: string }

interface MetaIDEState {
  activeTab: ActiveTab
  activeSidebar: SidebarTab
  showSidebar: boolean
  activePanel: PanelTab
  showPanel: boolean
  panelMaximized: boolean
  sidebarWidth: number
  panelHeight: number
  repositories: Repository[]
  workspace: WorkspaceData | null
  roadmap: RoadmapData | null
  risks: RiskItem[]
  overallRisk: string
  observation: WorkspaceObservation | null
  previewExpanded: boolean
  loading: boolean
  error: string | null

  vpsTree: FileEntry[]
  windowsTree: FileEntry[]
  fileMeshNodes: FileMeshNode[]
  windowsOnline: boolean
  vpsExpanded: boolean
  windowsExpanded: boolean
  expandedDirs: Set<string>

  setActiveTab: (tab: ActiveTab) => void
  setActiveSidebar: (tab: SidebarTab) => void
  setShowSidebar: (show: boolean) => void
  toggleSidebarTab: (tab: SidebarTab) => void
  setActivePanel: (tab: PanelTab) => void
  setShowPanel: (show: boolean) => void
  togglePanel: () => void
  togglePanelMaximized: () => void
  setSidebarWidth: (w: number) => void
  setPanelHeight: (h: number) => void
  setVpsTree: (entries: FileEntry[]) => void
  setWindowsTree: (entries: FileEntry[]) => void
  setFileMeshNodes: (nodes: FileMeshNode[]) => void
  setWindowsOnline: (online: boolean) => void
  setVpsExpanded: (v: boolean) => void
  setWindowsExpanded: (v: boolean) => void
  toggleDir: (path: string) => void
  isDirExpanded: (path: string) => boolean
  setPreviewExpanded: (expanded: boolean) => void
  togglePreviewExpanded: () => void
  fetchRepositories: () => Promise<void>
  fetchWorkspace: () => Promise<void>
  fetchRoadmap: () => Promise<void>
  fetchRisks: () => Promise<void>
  fetchObservation: () => Promise<void>
}

export const useMetaIDEStore = create<MetaIDEState>((set) => ({
  activeTab: 'files',
  activeSidebar: 'files',
  showSidebar: true,
  activePanel: 'terminal',
  showPanel: true,
  panelMaximized: false,
  sidebarWidth: 240,
  panelHeight: 240,
  repositories: [],
  workspace: null,
  roadmap: null,
  risks: [],
  overallRisk: 'none',
  previewExpanded: false,
  observation: null,
  loading: false,
  error: null,

  vpsTree: [],
  windowsTree: [],
  fileMeshNodes: [],
  windowsOnline: false,
  vpsExpanded: true,
  windowsExpanded: true,
  expandedDirs: new Set<string>(),

  setPreviewExpanded: (expanded) => set({ previewExpanded: expanded }),
  togglePreviewExpanded: () => set((s) => ({ previewExpanded: !s.previewExpanded })),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setActiveSidebar: (tab) => set({ activeSidebar: tab, showSidebar: true }),
  setShowSidebar: (show) => set({ showSidebar: show }),
  toggleSidebarTab: (tab) => set((s) => {
    if (s.activeSidebar === tab && s.showSidebar) return { showSidebar: false }
    return { activeSidebar: tab, showSidebar: true }
  }),
  setActivePanel: (tab) => set({ activePanel: tab }),
  setShowPanel: (show) => set({ showPanel: show, panelMaximized: show ? undefined : false } as Partial<MetaIDEState>),
  togglePanel: () => set((s) => ({ showPanel: !s.showPanel, panelMaximized: !s.showPanel ? s.panelMaximized : false })),
  togglePanelMaximized: () => set((s) => ({ panelMaximized: !s.panelMaximized })),
  setSidebarWidth: (w) => set({ sidebarWidth: Math.max(150, Math.min(400, w)) }),
  setPanelHeight: (h) => set({ panelHeight: Math.max(100, Math.min(600, h)) }),

  setVpsTree: (entries) => set({ vpsTree: entries }),
  setWindowsTree: (entries) => set({ windowsTree: entries }),
  setFileMeshNodes: (nodes) => {
    const online = nodes.some((n) => n.os === 'windows' && (n.status === 'connected' || n.status === 'online'))
    set({ fileMeshNodes: nodes, windowsOnline: online })
  },
  setWindowsOnline: (online) => set({ windowsOnline: online }),
  setVpsExpanded: (v) => set({ vpsExpanded: v }),
  setWindowsExpanded: (v) => set({ windowsExpanded: v }),
  toggleDir: (path) => set((s) => {
    const next = new Set(s.expandedDirs)
    if (next.has(path)) next.delete(path); else next.add(path)
    return { expandedDirs: next }
  }),
  isDirExpanded: (path) => useMetaIDEStore.getState().expandedDirs.has(path),

  fetchRepositories: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<{ repositories: Repository[]; generated_at: number }>(
        '/meta-ide/repositories',
      )
      set({ repositories: data.repositories, loading: false })
    } catch (err) {
      set({ error: String(err), loading: false })
    }
  },

  fetchWorkspace: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<WorkspaceData>('/meta-ide/workspace')
      set({ workspace: data, loading: false })
    } catch (err) {
      set({ error: String(err), loading: false })
    }
  },

  fetchRoadmap: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<RoadmapData>('/meta-ide/roadmap')
      set({ roadmap: data, loading: false })
    } catch (err) {
      set({ error: String(err), loading: false })
    }
  },

  fetchRisks: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<{ risks: RiskItem[]; overall_risk: string }>(
        '/meta-ide/risks',
      )
      set({ risks: data.risks, overallRisk: data.overall_risk, loading: false })
    } catch (err) {
      set({ error: String(err), loading: false })
    }
  },

  fetchObservation: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi<WorkspaceObservation>(
        '/meta-ide/workspace-observation',
      )
      set({ observation: data, loading: false })
    } catch (err) {
      set({ error: String(err), loading: false })
    }
  },
}))
