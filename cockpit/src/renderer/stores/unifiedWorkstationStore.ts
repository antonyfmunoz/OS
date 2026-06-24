import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface OvernightStatus {
  safe_count: number
  pending_count: number
  blocked_count: number
}

interface WorkstationNode {
  id?: string
  name?: string
  status?: string
  [key: string]: unknown
}

interface WorkstationSnapshot {
  workstation_state: string
  organism_mode: string
  execution_state: string
  presence_mode: string
  active_project: string
  active_repo: string
  active_panel: string
  pending_approvals: number
  active_delegations: number
  active_risks: Record<string, unknown>[]
  attention_items: Record<string, unknown>[]
  subsystem_health: Record<string, unknown>[]
  organism_health: string
  coherence_score: number
  generated_at: number

  continuity_state: string
  valid_transitions: string[]
  lifecycle_mode: string
  risk_ceiling: string
  effective_posture: string
  active_profile_modes: string[]
  overnight: OvernightStatus
  node_count: number
  nodes: WorkstationNode[]
  stt_available: boolean
  tts_available: boolean
}

const EMPTY_SNAPSHOT: WorkstationSnapshot = {
  workstation_state: 'idle',
  organism_mode: 'idle',
  execution_state: 'idle',
  presence_mode: 'listening',
  active_project: '',
  active_repo: '',
  active_panel: '',
  pending_approvals: 0,
  active_delegations: 0,
  active_risks: [],
  attention_items: [],
  subsystem_health: [],
  organism_health: 'unknown',
  coherence_score: 0,
  generated_at: 0,

  continuity_state: 'ACTIVE',
  valid_transitions: [],
  lifecycle_mode: 'day_cycle',
  risk_ceiling: 'HIGH',
  effective_posture: '',
  active_profile_modes: [],
  overnight: { safe_count: 0, pending_count: 0, blocked_count: 0 },
  node_count: 0,
  nodes: [],
  stt_available: false,
  tts_available: false,
}

interface UnifiedWorkstationState {
  snapshot: WorkstationSnapshot
  loading: boolean

  fetchSnapshot: () => Promise<void>
}

export const useUnifiedWorkstationStore = create<UnifiedWorkstationState>((set) => ({
  snapshot: EMPTY_SNAPSHOT,
  loading: false,

  fetchSnapshot: async () => {
    try {
      const data = await fetchApi<WorkstationSnapshot>('/unified-workstation/snapshot')
      set({
        snapshot: {
          ...EMPTY_SNAPSHOT,
          ...data,
          overnight: { ...EMPTY_SNAPSHOT.overnight, ...(data.overnight || {}) },
        },
      })
    } catch {
      /* keep stale — better than blanking */
    }
  },
}))
