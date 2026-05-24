import { create } from 'zustand'
import { fetchApi } from '../api/client'

export type ExecutionLayer = 'native' | 'container' | 'wsl' | 'vm'

interface ActionLogEntry {
  step: number
  action_type: string
  params: Record<string, unknown>
  result: Record<string, unknown>
  authority_class: string
  approved: boolean
}

interface ExecutionSlot {
  slot: number
  layer: ExecutionLayer
  task: string
  status: 'idle' | 'running' | 'paused' | 'stopped' | 'error'
  stepCount: number
  authorityClass: string
  riskClass: string
  approvalStatus: string
  actionLog: ActionLogEntry[]
}

interface AuthorityPreview {
  layer: string
  authority_class: string
  risk_class: string
  approval_requirement: string
}

interface ExecutionState {
  slots: ExecutionSlot[]
  selectedSlot: number
  authorityPreview: AuthorityPreview | null

  fetchStatus: () => Promise<void>
  fetchLog: (slot: number) => Promise<void>
  previewAuthority: (layer: ExecutionLayer) => Promise<void>
  startExecution: (layer: ExecutionLayer, task: string) => Promise<void>
  stopExecution: (slot: number) => Promise<void>
  pauseExecution: (slot: number) => Promise<void>
  resumeExecution: (slot: number) => Promise<void>
  selectSlot: (slot: number) => void
}

export const useExecutionStore = create<ExecutionState>((set, get) => ({
  slots: [],
  selectedSlot: 0,
  authorityPreview: null,

  fetchStatus: async () => {
    try {
      const data = await fetchApi<{ slots: Array<{
        slot: number
        layer: string
        task: string
        status: string
        step_count: number
        authority_class: string
        risk_class: string
        approval_status: string
      }> }>('/execution/status')
      set({
        slots: data.slots.map((s) => ({
          slot: s.slot,
          layer: s.layer as ExecutionLayer,
          task: s.task,
          status: s.status as ExecutionSlot['status'],
          stepCount: s.step_count,
          authorityClass: s.authority_class,
          riskClass: s.risk_class,
          approvalStatus: s.approval_status,
          actionLog: [],
        })),
      })
    } catch {
      // status fetch non-critical
    }
  },

  fetchLog: async (slot) => {
    try {
      const data = await fetchApi<{ slot: number; log: ActionLogEntry[] }>(
        `/execution/log?slot=${slot}`
      )
      set((s) => ({
        slots: s.slots.map((sl) =>
          sl.slot === slot ? { ...sl, actionLog: data.log } : sl
        ),
      }))
    } catch {
      // log fetch non-critical
    }
  },

  previewAuthority: async (layer) => {
    try {
      const data = await fetchApi<AuthorityPreview>(
        `/execution/authority?layer=${layer}`
      )
      set({ authorityPreview: data })
    } catch {
      set({ authorityPreview: null })
    }
  },

  startExecution: async (layer, task) => {
    try {
      const slot = get().selectedSlot
      await fetchApi('/execution/start', {
        method: 'POST',
        body: JSON.stringify({ task, layer, slot }),
      })
      get().fetchStatus()
    } catch {
      // start failure
    }
  },

  stopExecution: async (slot) => {
    try {
      await fetchApi('/execution/stop', {
        method: 'POST',
        body: JSON.stringify({ slot }),
      })
      get().fetchStatus()
    } catch {
      // stop failure
    }
  },

  pauseExecution: async (slot) => {
    try {
      await fetchApi('/execution/pause', {
        method: 'POST',
        body: JSON.stringify({ slot }),
      })
      get().fetchStatus()
    } catch {
      // pause failure
    }
  },

  resumeExecution: async (slot) => {
    try {
      await fetchApi('/execution/resume', {
        method: 'POST',
        body: JSON.stringify({ slot }),
      })
      get().fetchStatus()
    } catch {
      // resume failure
    }
  },

  selectSlot: (slot) => set({ selectedSlot: slot }),
}))
