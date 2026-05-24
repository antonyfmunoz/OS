import { create } from 'zustand'

export type MicState = 'idle' | 'listening' | 'processing'
export type TtsState = 'idle' | 'speaking'

interface VoiceState {
  micState: MicState
  ttsState: TtsState
  vadActive: boolean
  audioLevel: number
  lastTranscript: string

  setMicState: (state: MicState) => void
  setTtsState: (state: TtsState) => void
  setVadActive: (active: boolean) => void
  setAudioLevel: (level: number) => void
  setLastTranscript: (text: string) => void
}

export const useVoiceStore = create<VoiceState>((set) => ({
  micState: 'idle',
  ttsState: 'idle',
  vadActive: false,
  audioLevel: 0,
  lastTranscript: '',

  setMicState: (micState) => set({ micState }),
  setTtsState: (ttsState) => set({ ttsState }),
  setVadActive: (vadActive) => set({ vadActive }),
  setAudioLevel: (audioLevel) => set({ audioLevel }),
  setLastTranscript: (lastTranscript) => set({ lastTranscript }),
}))
