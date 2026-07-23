// Execution attempt store — the cockpit's read/act client for the canonical
// execution surface. Doctrine (mirrors objectivePlanStore): the SERVER is the
// sole authority. Every mutate (cancel/retry) is followed by a canonical
// re-GET; the POST echo is NEVER trusted as truth. No localStorage/sessionStorage
// — persistence through refresh/Chrome-restart is persistence-by-refetch against
// the backend attempt ledger. Execution DECISIONS are not here — they are
// HUD-only (unifiedApprovalStore).
import { create } from 'zustand'
import { ApiError, fetchApi } from '../api/client'

export interface AttemptRow {
  attempt_id: string
  task_id: string
  plan_record_id: string
  plan_version: number
  decision_ref: string
  attempt_number: number
  status: string
  phase: string
  blocked_reason: string
  worker_identity: string
  assignment_id: string
  lease_id: string
  verifier_role_id: string
  proof_id: string
  retry_of_attempt_id: string
  correlation_id: string
  created_at: number
  updated_at: number
}

export interface AttemptDetail extends AttemptRow {
  transitions?: Array<Record<string, unknown>>
  assignment?: Record<string, unknown> | null
  environment_lease?: Record<string, unknown> | null
  files_changed?: string[]
  commits?: string[]
  cancel_allowed?: boolean
  retry_allowed?: boolean
}

export interface FrontierRow {
  packet_id: string
  plan_record_id: string
  decision_ref: string
  attempt_count: number
  active: boolean
}

export interface OverlayEntry {
  attempt_count: number
  active_phase: string
  assigned_role: string
  blocker_state: string
  proof_id: string
}

interface ExecutionAttemptState {
  attempts: AttemptRow[]
  attemptById: Record<string, AttemptDetail>
  frontier: FrontierRow[]
  overlayByPacket: Record<string, OverlayEntry>
  byPlan: Record<string, { attempts: AttemptRow[] }>
  loading: boolean
  error: string | null
  conflict: boolean
  actingAttemptId: string | null

  fetchAttempts: (filters?: { status?: string; plan_record_id?: string; packet_id?: string }) => Promise<void>
  fetchAttempt: (attemptId: string) => Promise<AttemptDetail | null>
  fetchFrontier: () => Promise<void>
  fetchByPlan: (planRecordId: string) => Promise<void>
  fetchOverlay: (packetIds: string[]) => Promise<void>
  cancel: (attemptId: string, reason?: string) => Promise<boolean>
  retry: (attemptId: string) => Promise<boolean>
}

export const useExecutionAttemptStore = create<ExecutionAttemptState>((set, get) => ({
  attempts: [],
  attemptById: {},
  frontier: [],
  overlayByPacket: {},
  byPlan: {},
  loading: false,
  error: null,
  conflict: false,
  actingAttemptId: null,

  fetchAttempts: async (filters = {}) => {
    set({ loading: true })
    try {
      const qs = new URLSearchParams()
      if (filters.status) qs.set('status', filters.status)
      if (filters.plan_record_id) qs.set('plan_record_id', filters.plan_record_id)
      if (filters.packet_id) qs.set('packet_id', filters.packet_id)
      const suffix = qs.toString() ? `?${qs.toString()}` : ''
      const data = await fetchApi<{ attempts: AttemptRow[] }>(`/execution/attempts${suffix}`)
      set({ attempts: data?.attempts ?? [], error: null, loading: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false })
    }
  },

  fetchAttempt: async (attemptId: string) => {
    try {
      const data = await fetchApi<AttemptDetail | { error: string }>(
        `/execution/attempts/${attemptId}`,
      )
      const detail =
        data && !('error' in data) && (data as AttemptDetail).attempt_id ? (data as AttemptDetail) : null
      if (detail) {
        set((s) => ({ attemptById: { ...s.attemptById, [detail.attempt_id]: detail }, error: null }))
      }
      return detail
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) })
      return null
    }
  },

  fetchFrontier: async () => {
    try {
      const data = await fetchApi<{ frontier: FrontierRow[] }>('/execution/frontier')
      set({ frontier: data?.frontier ?? [] })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) })
    }
  },

  fetchByPlan: async (planRecordId: string) => {
    try {
      const data = await fetchApi<{ attempts: AttemptRow[] }>(`/execution/by-plan/${planRecordId}`)
      set((s) => ({ byPlan: { ...s.byPlan, [planRecordId]: { attempts: data?.attempts ?? [] } } }))
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) })
    }
  },

  fetchOverlay: async (packetIds: string[]) => {
    if (packetIds.length === 0) return
    try {
      const data = await fetchApi<{ overlay: Record<string, OverlayEntry> }>(
        `/execution/overlay?packet_ids=${encodeURIComponent(packetIds.join(','))}`,
      )
      set((s) => ({ overlayByPacket: { ...s.overlayByPacket, ...(data?.overlay ?? {}) } }))
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) })
    }
  },

  cancel: async (attemptId: string, reason = '') => {
    set({ actingAttemptId: attemptId, conflict: false })
    try {
      await fetchApi(`/execution/attempts/${attemptId}/cancel`, {
        method: 'POST',
        body: JSON.stringify({ reason, decided_by: 'operator' }),
      })
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        set({ conflict: true, actingAttemptId: null })
        // Reread to reconcile with canonical truth even on conflict.
        await get().fetchAttempt(attemptId)
        return false
      }
      set({ error: err instanceof Error ? err.message : String(err), actingAttemptId: null })
      return false
    }
    // Never trust the POST echo — reread canonical truth.
    const reread = await get().fetchAttempt(attemptId)
    await get().fetchAttempts()
    set({ actingAttemptId: null })
    return reread?.status === 'cancelled'
  },

  retry: async (attemptId: string) => {
    set({ actingAttemptId: attemptId, conflict: false })
    try {
      await fetchApi(`/execution/attempts/${attemptId}/retry`, {
        method: 'POST',
        body: JSON.stringify({ decided_by: 'operator' }),
      })
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        set({ conflict: true, actingAttemptId: null })
        return false
      }
      set({ error: err instanceof Error ? err.message : String(err), actingAttemptId: null })
      return false
    }
    // Reread — the scheduler mints the linked retry; reflect canonical state.
    await get().fetchAttempts()
    set({ actingAttemptId: null })
    return true
  },
}))
