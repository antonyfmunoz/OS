import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface RecoveryAction {
  action: string
  work_id: string
  reason: string
  auto_recoverable: boolean
}

interface RecoveryAssessment {
  work_id: string
  state: string
  actions: RecoveryAction[]
  assessed_at: number
  journal_entries?: JournalEntry[]
}

interface JournalEntry {
  phase: string
  source: string
  details: string
  timestamp: number
}

interface FailureItem {
  work_id: string
  status: string
  description: string
  risk_class: string
  created_at: number
}

interface FailureRecord {
  failure_type: string
  message: string
  timestamp: number
  recovery_attempted: boolean
}

interface RecoverySummary {
  total_recoverable: number
  failed: number
  blocked: number
  interrupted: number
  runtime_available: boolean
}

interface RecoveryHistoryEntry {
  work_id: string
  action_type: string
  reason: string
  timestamp: number
  state_before: string
}

interface RecoveryDashboardState {
  queue: RecoveryAssessment[]
  selectedItem: RecoveryAssessment | null
  failures: FailureItem[]
  failureHistory: FailureRecord[]
  summary: RecoverySummary | null
  actionHistory: RecoveryHistoryEntry[]
  loading: boolean
  error: string | null
  actionResult: string | null

  fetchSummary: () => Promise<void>
  fetchQueue: () => Promise<void>
  fetchQueueDetail: (workId: string) => Promise<void>
  fetchFailures: () => Promise<void>
  fetchFailureHistory: (workId: string) => Promise<void>
  fetchActions: (workId: string) => Promise<RecoveryAction[]>
  executeAction: (workId: string, actionType: string, reason?: string) => Promise<boolean>
  fetchHistory: (limit?: number) => Promise<void>
  clearSelection: () => void
}

export const useRecoveryDashboardStore = create<RecoveryDashboardState>((set, get) => ({
  queue: [],
  selectedItem: null,
  failures: [],
  failureHistory: [],
  summary: null,
  actionHistory: [],
  loading: false,
  error: null,
  actionResult: null,

  fetchSummary: async () => {
    try {
      const data = await fetchApi('/recovery/summary')
      set({ summary: data as RecoverySummary })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchQueue: async () => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi('/recovery/queue')
      set({ queue: (data as { items: RecoveryAssessment[] }).items, loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  fetchQueueDetail: async (workId: string) => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi(`/recovery/queue/${workId}`)
      set({ selectedItem: data as RecoveryAssessment, loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  fetchFailures: async () => {
    try {
      const data = await fetchApi('/recovery/failures')
      set({ failures: (data as { failures: FailureItem[] }).failures })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchFailureHistory: async (workId: string) => {
    try {
      const data = await fetchApi(`/recovery/failures/${workId}/history`)
      set({ failureHistory: (data as { history: FailureRecord[] }).history })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchActions: async (workId: string) => {
    try {
      const data = await fetchApi(`/recovery/actions/${workId}`)
      return (data as { actions: RecoveryAction[] }).actions
    } catch {
      return []
    }
  },

  executeAction: async (workId: string, actionType: string, reason = '') => {
    set({ actionResult: null, error: null })
    try {
      const data = await fetchApi('/recovery/execute', {
        method: 'POST',
        body: JSON.stringify({ work_id: workId, action_type: actionType, reason }),
      })
      set({ actionResult: `${actionType} executed for ${workId}` })
      await get().fetchQueue()
      await get().fetchSummary()
      return true
    } catch (e) {
      set({ error: String(e) })
      return false
    }
  },

  fetchHistory: async (limit = 50) => {
    try {
      const data = await fetchApi(`/recovery/history?limit=${limit}`)
      set({ actionHistory: (data as { history: RecoveryHistoryEntry[] }).history })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  clearSelection: () => set({ selectedItem: null, failureHistory: [], actionResult: null }),
}))
