import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface ProofPackage {
  proof_id: string
  request_id: string
  execution_id: string
  packet_id: string
  description: string
  status: string
  files_changed: string[]
  commands_run: string[]
  logs: string[]
  verification_results: Record<string, unknown>[]
  browser_evidence: string[]
  review_notes: string
  reviewed_by: string
  created_at: number
  reviewed_at: number
  evidence_files?: EvidenceFile[]
}

interface EvidenceFile {
  name: string
  size: number
  modified: number
  type: string
}

interface TimelineEntry {
  phase: string
  source: string
  details: string
  timestamp: number
}

interface ProofSummary {
  total: number
  by_status: Record<string, number>
  store_available: boolean
}

interface ObsArtifact {
  [key: string]: unknown
}

interface ProofInspectorState {
  packages: ProofPackage[]
  selectedProof: ProofPackage | null
  timeline: TimelineEntry[]
  summary: ProofSummary | null
  artifacts: ObsArtifact[]
  loading: boolean
  error: string | null

  fetchSummary: () => Promise<void>
  fetchPackages: (status?: string, limit?: number, offset?: number) => Promise<void>
  fetchProofDetail: (proofId: string) => Promise<void>
  fetchTimeline: (proofId: string) => Promise<void>
  fetchEvidence: (proofId: string) => Promise<EvidenceFile[]>
  fetchRaw: (proofId: string) => Promise<ProofPackage | null>
  fetchArtifacts: (limit?: number) => Promise<void>
  approveProof: (proofId: string, notes?: string) => Promise<boolean>
  rejectProof: (proofId: string, notes?: string) => Promise<boolean>
  clearSelection: () => void
}

export const useProofInspectorStore = create<ProofInspectorState>((set, get) => ({
  packages: [],
  selectedProof: null,
  timeline: [],
  summary: null,
  artifacts: [],
  loading: false,
  error: null,

  fetchSummary: async () => {
    try {
      const data = await fetchApi('/proof-inspector/summary')
      set({ summary: data as ProofSummary })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchPackages: async (status = '', limit = 50, offset = 0) => {
    set({ loading: true, error: null })
    try {
      const params = new URLSearchParams()
      if (status) params.set('status', status)
      params.set('limit', String(limit))
      params.set('offset', String(offset))
      const data = await fetchApi(`/proof-inspector/packages?${params}`)
      set({ packages: (data as { packages: ProofPackage[] }).packages, loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  fetchProofDetail: async (proofId: string) => {
    set({ loading: true, error: null })
    try {
      const data = await fetchApi(`/proof-inspector/packages/${proofId}`)
      set({ selectedProof: data as ProofPackage, loading: false })
    } catch (e) {
      set({ error: String(e), loading: false })
    }
  },

  fetchTimeline: async (proofId: string) => {
    try {
      const data = await fetchApi(`/proof-inspector/packages/${proofId}/timeline`)
      set({ timeline: (data as { timeline: TimelineEntry[] }).timeline })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  fetchEvidence: async (proofId: string) => {
    try {
      const data = await fetchApi(`/proof-inspector/packages/${proofId}/evidence`)
      return (data as { evidence_files: EvidenceFile[] }).evidence_files || []
    } catch {
      return []
    }
  },

  fetchRaw: async (proofId: string) => {
    try {
      const data = await fetchApi(`/proof-inspector/packages/${proofId}/raw`)
      return data as ProofPackage
    } catch {
      return null
    }
  },

  fetchArtifacts: async (limit = 50) => {
    try {
      const data = await fetchApi(`/proof-inspector/artifacts?limit=${limit}`)
      set({ artifacts: (data as { artifacts: ObsArtifact[] }).artifacts })
    } catch (e) {
      set({ error: String(e) })
    }
  },

  approveProof: async (proofId: string, notes = '') => {
    try {
      await fetchApi(`/proof-inspector/packages/${proofId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      })
      await get().fetchPackages()
      await get().fetchSummary()
      return true
    } catch {
      return false
    }
  },

  rejectProof: async (proofId: string, notes = '') => {
    try {
      await fetchApi(`/proof-inspector/packages/${proofId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      })
      await get().fetchPackages()
      await get().fetchSummary()
      return true
    } catch {
      return false
    }
  },

  clearSelection: () => set({ selectedProof: null, timeline: [] }),
}))
