import { create } from 'zustand'

export type MicState =
  | 'idle'
  | 'requesting_permission'
  | 'connecting_voice_ws'
  | 'listening'
  | 'recording'
  | 'transcribing'
  | 'processing'
  | 'interrupted'

export type TtsState = 'idle' | 'generating_tts' | 'ready_to_speak' | 'speaking' | 'tts_failed'
export type ActivationMode = 'manual' | 'wake_word' | 'clap' | 'always_on'

/** Presentation lifecycle for organism response commit. */
export type PresentationStatus =
  | 'idle'
  | 'thinking'
  | 'preparing_response'
  | 'preparing_voice'
  | 'ready_to_commit'
  | 'committing'
  | 'presenting'
  | 'complete'

/** Envelope that holds a DEX response until text+audio are ready to commit together. */
export interface OrganismResponseEnvelope {
  messageId: string
  content: string
  spokenText: string
  metadata: Record<string, unknown>
  ttsReady: boolean
  ttsError: string | null
  voiceTurnId: string
}

export type VoiceOutcome =
  | 'TRANSCRIPT_RECEIVED'
  | 'NO_SPEECH_DETECTED'
  | 'MIC_PERMISSION_DENIED'
  | 'MIC_DEVICE_UNAVAILABLE'
  | 'VOICE_WS_UNAVAILABLE'
  | 'STT_FAILED'
  | 'TIMEOUT'
  | 'RECORDING_FORMAT_UNSUPPORTED'

interface VoiceState {
  micState: MicState
  ttsState: TtsState
  vadActive: boolean
  audioLevel: number
  lastTranscript: string
  activationMode: ActivationMode
  wakeWordEnabled: boolean
  clapEnabled: boolean
  alwaysOnEnabled: boolean
  error: string | null
  pendingVoiceResponse: boolean
  lastOutcome: VoiceOutcome | null
  chunksSent: number
  voicePresentationStatus: PresentationStatus
  activeTtsJobId: string | null
  heldEnvelope: OrganismResponseEnvelope | null

  setMicState: (state: MicState) => void
  setTtsState: (state: TtsState) => void
  setVadActive: (active: boolean) => void
  setAudioLevel: (level: number) => void
  setLastTranscript: (text: string) => void
  setActivationMode: (mode: ActivationMode) => void
  setWakeWordEnabled: (enabled: boolean) => void
  setClapEnabled: (enabled: boolean) => void
  setAlwaysOnEnabled: (enabled: boolean) => void
  setError: (error: string | null) => void
  setPendingVoiceResponse: (pending: boolean) => void
  setLastOutcome: (outcome: VoiceOutcome | null) => void
  setChunksSent: (n: number) => void
  incrementChunksSent: () => void
  setVoicePresentationStatus: (status: PresentationStatus) => void
  setActiveTtsJobId: (id: string | null) => void
  setHeldEnvelope: (envelope: OrganismResponseEnvelope | null) => void
  reset: () => void
}

export const useVoiceStore = create<VoiceState>((set) => ({
  micState: 'idle',
  ttsState: 'idle',
  vadActive: false,
  audioLevel: 0,
  lastTranscript: '',
  activationMode: 'manual',
  wakeWordEnabled: false,
  clapEnabled: false,
  alwaysOnEnabled: false,
  error: null,
  pendingVoiceResponse: false,
  lastOutcome: null,
  chunksSent: 0,
  voicePresentationStatus: 'idle',
  activeTtsJobId: null,
  heldEnvelope: null,

  setMicState: (micState) => set({ micState }),
  setTtsState: (ttsState) => set({ ttsState }),
  setVadActive: (vadActive) => set({ vadActive }),
  setAudioLevel: (audioLevel) => set({ audioLevel }),
  setLastTranscript: (lastTranscript) => set({ lastTranscript }),
  setActivationMode: (activationMode) => set({ activationMode }),
  setWakeWordEnabled: (wakeWordEnabled) => set({ wakeWordEnabled }),
  setClapEnabled: (clapEnabled) => set({ clapEnabled }),
  setAlwaysOnEnabled: (alwaysOnEnabled) => set({ alwaysOnEnabled }),
  setError: (error) => set({ error }),
  setPendingVoiceResponse: (pendingVoiceResponse) => set({ pendingVoiceResponse }),
  setLastOutcome: (lastOutcome) => set({ lastOutcome }),
  setChunksSent: (chunksSent) => set({ chunksSent }),
  incrementChunksSent: () => set((s) => ({ chunksSent: s.chunksSent + 1 })),
  setVoicePresentationStatus: (voicePresentationStatus) => set({ voicePresentationStatus }),
  setActiveTtsJobId: (activeTtsJobId) => set({ activeTtsJobId }),
  setHeldEnvelope: (heldEnvelope) => set({ heldEnvelope }),
  reset: () => set({
    micState: 'idle',
    ttsState: 'idle',
    vadActive: false,
    audioLevel: 0,
    error: null,
    pendingVoiceResponse: false,
    lastOutcome: null,
    chunksSent: 0,
    voicePresentationStatus: 'idle',
    activeTtsJobId: null,
    heldEnvelope: null,
  }),
}))
