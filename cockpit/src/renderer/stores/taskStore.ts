import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface Task {
  id: string
  title: string
  status: 'pending' | 'in_progress' | 'completed' | 'blocked'
  agent: string
  priority: string
  created_at: string
  updated_at: string
}

interface Workflow {
  id: string
  name: string
  schedule: string
  last_run: string | null
  last_status: string
  run_count: number
  avg_duration_ms: number
}

type ViewMode = 'tasks' | 'workflows' | 'timeline'

interface TaskState {
  tasks: Task[]
  workflows: Workflow[]
  viewMode: ViewMode
  loading: boolean

  fetchTasks: () => Promise<void>
  fetchWorkflows: () => Promise<void>
  setViewMode: (mode: ViewMode) => void
  triggerWorkflow: (id: string) => Promise<void>
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  workflows: [],
  viewMode: 'tasks',
  loading: false,

  fetchTasks: async () => {
    try {
      const data = await fetchApi<Task[]>('/api/umh/tasks')
      set({ tasks: data })
    } catch {
      set({ tasks: [] })
    }
  },

  fetchWorkflows: async () => {
    try {
      const data = await fetchApi<Workflow[]>('/api/umh/workflows')
      set({ workflows: data })
    } catch {
      set({ workflows: [] })
    }
  },

  setViewMode: (mode) => set({ viewMode: mode }),

  triggerWorkflow: async (id) => {
    await fetchApi(`/api/umh/workflows/${id}/trigger`, {
      method: 'POST',
      body: JSON.stringify({}),
    }).catch(() => {})
    get().fetchWorkflows()
  },
}))
