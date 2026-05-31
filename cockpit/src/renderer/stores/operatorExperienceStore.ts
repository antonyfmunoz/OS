import { create } from 'zustand'
import { fetchApi } from '../api/client'
import { speechAdapter } from '../operator/speechInputAdapter'
import type {
  VoiceCommandState,
  VoiceInputMode,
  VoiceTranscript,
  DexResponse,
  OperatorSession,
  SessionTurn,
  PacketPreview,
  TopologyPreview,
  PropagationPreview,
} from '../operator/voiceTypes'

interface OperatorOverview {
  status: string
  phase: string
  session_count: number
  recent_sessions: OperatorSession[]
}

interface StatusResponse {
  roadmap: Record<string, unknown>
  approvals: Record<string, unknown>
  system_state: string
}

interface ApprovalResponse {
  pending: ApprovalItem[]
  total: number
}

interface ApprovalItem {
  id: string
  description: string
  status: string
  required: boolean
  created_at: string
}

interface OperatorExperienceState {
  currentSession: OperatorSession | null
  sessions: OperatorSession[]
  activeInput: string
  voiceState: VoiceCommandState
  voiceSupported: boolean
  transcript: VoiceTranscript | null
  interimTranscript: string
  lastResponse: DexResponse | null
  responseHistory: SessionTurn[]
  pendingApprovals: ApprovalItem[]
  roadmapStatus: Record<string, unknown> | null
  loading: boolean
  error: string | null

  loadOverview: () => Promise<void>
  loadSessions: () => Promise<void>
  loadSession: (sessionId: string) => Promise<void>
  sendTextCommand: (text: string) => Promise<void>
  sendVoiceTranscript: (transcript: VoiceTranscript) => Promise<void>
  startVoiceInput: () => void
  stopVoiceInput: () => void
  clearTranscript: () => void
  submitCommand: () => Promise<void>
  loadStatus: () => Promise<void>
  loadApprovals: () => Promise<void>
  previewPacket: (intent: string) => Promise<PacketPreview | null>
  previewPropagation: (description: string) => Promise<PropagationPreview | null>
  previewTopology: (input: string) => Promise<TopologyPreview | null>
  setActiveInput: (text: string) => void
  reset: () => void
}

function generateSessionId(): string {
  return `ops-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
}

function parseDexResponse(data: Record<string, unknown>): DexResponse {
  return {
    session_id: (data.session_id as string) || '',
    intent: (data.intent as string) || (data.classified_intent as string) || '',
    summary: (data.summary as string) || (data.response as string) || '',
    current_state: (data.current_state as string) || null,
    recommended_next_action: (data.recommended_next_action as string) || null,
    confidence: (data.confidence as number) || 0,
    safety_state: (data.safety_state as string) || 'preview_only',
    packet_preview: (data.packet_preview as PacketPreview) || null,
    topology_preview: (data.topology_preview as TopologyPreview) || null,
    human_actions: (data.human_actions as DexResponse['human_actions']) || [],
    approval_gates: (data.approval_gates as DexResponse['approval_gates']) || [],
    propagation_preview: (data.propagation_preview as PropagationPreview) || null,
    execution_occurred: (data.execution_occurred as boolean) || false,
  }
}

export const useOperatorExperienceStore = create<OperatorExperienceState>((set, get) => {
  let voiceInitialized = false

  function initVoiceListeners(): void {
    if (voiceInitialized) return
    voiceInitialized = true

    speechAdapter.onStateChange((state) => {
      set({ voiceState: state })
    })

    speechAdapter.onInterimTranscript((t) => {
      set({ interimTranscript: t.text })
    })

    speechAdapter.onFinalTranscript((t) => {
      set({
        transcript: t,
        activeInput: t.text,
        interimTranscript: '',
      })
    })

    speechAdapter.onError((error) => {
      set({ error })
    })
  }

  return {
    currentSession: null,
    sessions: [],
    activeInput: '',
    voiceState: speechAdapter.isSupported() ? 'idle' : 'unsupported',
    voiceSupported: speechAdapter.isSupported(),
    transcript: null,
    interimTranscript: '',
    lastResponse: null,
    responseHistory: [],
    pendingApprovals: [],
    roadmapStatus: null,
    loading: false,
    error: null,

    loadOverview: async () => {
      set({ loading: true, error: null })
      try {
        const data = await fetchApi<OperatorOverview>('/organism/operator-experience')
        set({
          sessions: data.recent_sessions || [],
          loading: false,
        })
      } catch (e) {
        set({ error: (e as Error).message, loading: false })
      }
    },

    loadSessions: async () => {
      set({ loading: true, error: null })
      try {
        const data = await fetchApi<{ sessions: OperatorSession[] }>(
          '/organism/operator-experience/sessions'
        )
        set({ sessions: data.sessions || [], loading: false })
      } catch (e) {
        set({ error: (e as Error).message, loading: false })
      }
    },

    loadSession: async (sessionId: string) => {
      set({ loading: true, error: null })
      try {
        const data = await fetchApi<OperatorSession>(
          `/organism/operator-experience/sessions/${sessionId}`
        )
        set({
          currentSession: data,
          responseHistory: data.turns || [],
          loading: false,
        })
      } catch (e) {
        set({ error: (e as Error).message, loading: false })
      }
    },

    sendTextCommand: async (text: string) => {
      const sessionId = get().currentSession?.session_id || generateSessionId()
      set({ loading: true, error: null, voiceState: 'submitting' })
      try {
        const raw = await fetchApi<Record<string, unknown>>(
          '/organism/operator-experience/send',
          {
            method: 'POST',
            body: JSON.stringify({ input: text, session_id: sessionId }),
          }
        )
        const dexResponse = parseDexResponse(raw)
        const turn: SessionTurn = {
          turn_id: `turn-${Date.now()}`,
          input: text,
          input_mode: 'text' as VoiceInputMode,
          response: dexResponse,
          timestamp: new Date().toISOString(),
        }
        set((s) => ({
          lastResponse: dexResponse,
          responseHistory: [...s.responseHistory, turn],
          voiceState: 'responded',
          loading: false,
          activeInput: '',
          currentSession: s.currentSession
            ? { ...s.currentSession, turn_count: s.currentSession.turn_count + 1 }
            : {
                session_id: sessionId,
                created_at: new Date().toISOString(),
                last_activity: new Date().toISOString(),
                turn_count: 1,
                turns: [],
              },
        }))
      } catch (e) {
        set({ error: (e as Error).message, loading: false, voiceState: 'error' })
      }
    },

    sendVoiceTranscript: async (transcript: VoiceTranscript) => {
      const text = transcript.text
      if (!text.trim()) return
      const sessionId = get().currentSession?.session_id || generateSessionId()
      set({ loading: true, error: null, voiceState: 'submitting' })
      try {
        const raw = await fetchApi<Record<string, unknown>>(
          '/organism/operator-experience/send',
          {
            method: 'POST',
            body: JSON.stringify({ input: text, session_id: sessionId }),
          }
        )
        const dexResponse = parseDexResponse(raw)
        const turn: SessionTurn = {
          turn_id: `turn-${Date.now()}`,
          input: text,
          input_mode: 'voice' as VoiceInputMode,
          response: dexResponse,
          timestamp: new Date().toISOString(),
        }
        set((s) => ({
          lastResponse: dexResponse,
          responseHistory: [...s.responseHistory, turn],
          transcript: null,
          voiceState: 'responded',
          loading: false,
          activeInput: '',
          currentSession: s.currentSession
            ? { ...s.currentSession, turn_count: s.currentSession.turn_count + 1 }
            : {
                session_id: sessionId,
                created_at: new Date().toISOString(),
                last_activity: new Date().toISOString(),
                turn_count: 1,
                turns: [],
              },
        }))
      } catch (e) {
        set({ error: (e as Error).message, loading: false, voiceState: 'error' })
      }
    },

    startVoiceInput: () => {
      initVoiceListeners()
      const sessionId = get().currentSession?.session_id || generateSessionId()
      speechAdapter.startListening(sessionId)
    },

    stopVoiceInput: () => {
      speechAdapter.stopListening()
    },

    clearTranscript: () => {
      set({ transcript: null, interimTranscript: '', activeInput: '' })
    },

    submitCommand: async () => {
      const { activeInput, transcript } = get()
      if (transcript && transcript.source === 'browser_speech') {
        await get().sendVoiceTranscript({ ...transcript, text: activeInput || transcript.text })
      } else if (activeInput.trim()) {
        await get().sendTextCommand(activeInput)
      }
    },

    loadStatus: async () => {
      set({ loading: true, error: null })
      try {
        const data = await fetchApi<StatusResponse>('/organism/operator-experience/status')
        set({
          roadmapStatus: data.roadmap || null,
          loading: false,
        })
      } catch (e) {
        set({ error: (e as Error).message, loading: false })
      }
    },

    loadApprovals: async () => {
      set({ loading: true, error: null })
      try {
        const data = await fetchApi<ApprovalResponse>('/organism/operator-experience/approvals')
        set({
          pendingApprovals: data.pending || [],
          loading: false,
        })
      } catch (e) {
        set({ error: (e as Error).message, loading: false })
      }
    },

    previewPacket: async (intent: string): Promise<PacketPreview | null> => {
      try {
        const data = await fetchApi<Record<string, unknown>>(
          '/organism/operator-experience/packet-preview',
          {
            method: 'POST',
            body: JSON.stringify({ input: intent }),
          }
        )
        return (data.packet_preview as PacketPreview) || null
      } catch {
        return null
      }
    },

    previewPropagation: async (description: string): Promise<PropagationPreview | null> => {
      try {
        const data = await fetchApi<Record<string, unknown>>(
          '/organism/operator-experience/propagation-preview',
          {
            method: 'POST',
            body: JSON.stringify({ description }),
          }
        )
        return (data as unknown as PropagationPreview) || null
      } catch {
        return null
      }
    },

    previewTopology: async (input: string): Promise<TopologyPreview | null> => {
      try {
        const data = await fetchApi<Record<string, unknown>>(
          '/organism/operator-experience/topology-preview',
          {
            method: 'POST',
            body: JSON.stringify({ input }),
          }
        )
        return (data as unknown as TopologyPreview) || null
      } catch {
        return null
      }
    },

    setActiveInput: (text: string) => set({ activeInput: text }),

    reset: () =>
      set({
        currentSession: null,
        sessions: [],
        activeInput: '',
        voiceState: speechAdapter.isSupported() ? 'idle' : 'unsupported',
        transcript: null,
        interimTranscript: '',
        lastResponse: null,
        responseHistory: [],
        pendingApprovals: [],
        roadmapStatus: null,
        loading: false,
        error: null,
      }),
  }
})
