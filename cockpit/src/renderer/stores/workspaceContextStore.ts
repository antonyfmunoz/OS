import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { fetchApi } from '../api/client'

interface WorkspaceContext {
  activeProject: string
  activeRepo: string
  activeBranch: string
  activeFile: string
  activePreview: string
  activeExecution: string
  activePlan: string
  activePacket: string
  executorType: string
  targetMachine: string

  setActiveProject: (v: string) => void
  setActiveRepo: (v: string) => void
  setActiveBranch: (v: string) => void
  setActiveFile: (v: string) => void
  setActivePreview: (v: string) => void
  setActiveExecution: (v: string) => void
  setActivePlan: (v: string) => void
  setActivePacket: (v: string) => void
  setExecutorType: (v: string) => void
  setTargetMachine: (v: string) => void
  fetchContext: () => Promise<void>
  contextLine: () => string
}

export const useWorkspaceContextStore = create<WorkspaceContext>()(
  persist(
    (set, get) => ({
      activeProject: '',
      activeRepo: '',
      activeBranch: '',
      activeFile: '',
      activePreview: '',
      activeExecution: '',
      activePlan: '',
      activePacket: '',
      executorType: '',
      targetMachine: '',

      setActiveProject: (v) => set({ activeProject: v }),
      setActiveRepo: (v) => set({ activeRepo: v }),
      setActiveBranch: (v) => set({ activeBranch: v }),
      setActiveFile: (v) => set({ activeFile: v }),
      setActivePreview: (v) => set({ activePreview: v }),
      setActiveExecution: (v) => set({ activeExecution: v }),
      setActivePlan: (v) => set({ activePlan: v }),
      setActivePacket: (v) => set({ activePacket: v }),
      setExecutorType: (v) => set({ executorType: v }),
      setTargetMachine: (v) => set({ targetMachine: v }),

      fetchContext: async () => {
        try {
          const data = await fetchApi<Record<string, string>>('/api/umh/workspace/context')
          set({
            activeProject: data.active_project || get().activeProject,
            activeRepo: data.active_repo || get().activeRepo,
            activeBranch: data.active_branch || get().activeBranch,
            activeFile: data.active_file || get().activeFile,
            activePreview: data.active_preview || get().activePreview,
            activeExecution: data.active_execution || get().activeExecution,
            executorType: data.executor_type || get().executorType,
            targetMachine: data.target_machine || get().targetMachine,
          })
        } catch {
          // backend unavailable — keep local state
        }
      },

      contextLine: () => {
        const s = get()
        const parts: string[] = []
        if (s.activeProject) parts.push(s.activeProject)
        if (s.activeBranch) parts.push(s.activeBranch)
        if (s.activeFile) {
          const filename = s.activeFile.split('/').pop() || s.activeFile
          parts.push(filename)
        }
        if (s.executorType) {
          const isSim = s.executorType === 'simulation'
          parts.push(isSim ? 'SIM' : `LIVE${s.targetMachine ? ' • ' + s.targetMachine : ''}`)
        }
        return parts.join(' · ')
      },
    }),
    {
      name: 'umh-workspace-context',
      partialize: (state) => ({
        activeProject: state.activeProject,
        activeRepo: state.activeRepo,
        activeBranch: state.activeBranch,
        activeFile: state.activeFile,
        activePreview: state.activePreview,
        executorType: state.executorType,
        targetMachine: state.targetMachine,
      }),
    },
  ),
)
