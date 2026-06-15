import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface CycleEventData {
  result_id?: string
  work_packet_id?: string
  governance_decision_id?: string
  execution_bundle_id?: string | null
  memory_write_receipt_id?: string | null
  reality_update_id?: string | null
  final_status?: string
  steps_completed?: string[]
  total_duration_ms?: number
  active_domains?: string[]
  error?: string | null
}

interface CycleEvent {
  event_id: string
  event_type: string
  timestamp: number
  data: CycleEventData
}

interface LoopResult {
  result_id: string
  reality_snapshot_id: string
  work_packet_id: string
  governance_decision_id: string
  execution_bundle_id: string | null
  proof_artifact_ids: string[]
  memory_write_receipt_id: string | null
  reality_update_id: string | null
  event_ids: string[]
  steps_completed: string[]
  total_duration_ms: number
  final_status: string
  error: string | null
}

interface OrganismLoopState {
  cycles: CycleEvent[]
  lastResult: LoopResult | null
  loading: boolean
  executing: boolean
  error: string | null

  fetchCycles: () => Promise<void>
  executeIntent: (intent: string, desiredEndState?: string) => Promise<void>
}

export const useOrganismLoopStore = create<OrganismLoopState>((set) => ({
  cycles: [],
  lastResult: null,
  loading: false,
  executing: false,
  error: null,

  fetchCycles: async () => {
    try {
      set({ loading: true })
      const data = await fetchApi<{ cycles: CycleEvent[]; count: number }>(
        '/organism/loop/status',
      )
      set({ cycles: data.cycles, loading: false })
    } catch {
      set({ error: 'Failed to fetch loop cycles', loading: false })
    }
  },

  executeIntent: async (intent: string, desiredEndState?: string) => {
    set({ executing: true, error: null, lastResult: null })
    try {
      const body: Record<string, string> = { intent }
      if (desiredEndState) body.desired_end_state = desiredEndState
      const result = await fetchApi<LoopResult>('/organism/loop/execute', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      set({ lastResult: result, executing: false })
    } catch {
      set({ error: 'Failed to execute intent', executing: false })
    }
  },
}))
