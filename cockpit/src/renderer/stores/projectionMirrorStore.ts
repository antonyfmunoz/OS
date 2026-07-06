// Projection mirror stores — P4S-30.
//
// Thin read-only clients for the LyfeOS and CreatorOS activation/readiness
// surfaces (GET /api/umh/lyfeos/activation, GET /api/umh/creatoros/activation
// — transports/api/cockpit_core_lyfeos_routes.py /
// cockpit_core_creatoros_routes.py, backed by the projection-owned
// eos_readiness()-shaped accessors in
// projections/lyfeos/integration/readiness.py and
// projections/creatoros/integration/readiness.py). MIRROR, NOT UX COLLAPSE:
// this store only ever reads and reflects that response — it never mutates
// projection state and never reimplements projection-native features
// (journals, feeds, etc). One factory produces one independent store per
// projection so each panel/component polls and errors independently, same
// as every other per-projection store in this directory (compare
// eosActionQueueStore.ts).
import { create } from 'zustand'
import { fetchApi } from '../api/client'

export interface ProjectionMirrorSeed {
  app_name: string | null
  health_url: string | null
  public_url: string | null
  l4_workflow: string | null
}

export interface ProjectionMirrorReadiness {
  projection_id: string
  registered_in_seed: boolean
  runtime_registered: boolean
  seed: ProjectionMirrorSeed
  connection_status: string
  boot_eligible: boolean
  poll_interval: number | null
  error?: string | null
}

interface ProjectionMirrorState {
  readiness: ProjectionMirrorReadiness | null
  loading: boolean
  error: string | null
  fetchReadiness: () => Promise<void>
}

function createProjectionMirrorStore(endpoint: string) {
  return create<ProjectionMirrorState>((set) => ({
    readiness: null,
    loading: false,
    error: null,

    fetchReadiness: async () => {
      set({ loading: true })
      try {
        const data = await fetchApi<ProjectionMirrorReadiness>(endpoint)
        set({ readiness: data, error: data.error ?? null, loading: false })
      } catch (err) {
        set({ error: err instanceof Error ? err.message : String(err), loading: false })
      }
    },
  }))
}

// One independent store per projection — same isolation model as every
// other per-projection store in this directory.
export const useLyfeOSMirrorStore = createProjectionMirrorStore('/lyfeos/activation')
export const useCreatorOSMirrorStore = createProjectionMirrorStore('/creatoros/activation')
