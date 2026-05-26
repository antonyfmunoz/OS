import { create } from 'zustand'

export type MicState = 'idle' | 'listening' | 'processing'
export type TtsState = 'idle' | 'speaking'
export type ActivationMode = 'manual' | 'wake_word' | 'clap' | 'always_on'

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

  setMicState: (state: MicState) => void
  setTtsState: (state: TtsState) => void
  setVadActive: (active: boolean) => void
  setAudioLevel: (level: number) => void
  setLastTranscript: (text: string) => void
  setActivationMode: (mode: ActivationMode) => void
  setWakeWordEnabled: (enabled: boolean) => void
  setClapEnabled: (enabled: boolean) => void
  setAlwaysOnEnabled: (enabled: boolean) => void
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

  setMicState: (micState) => set({ micState }),
  setTtsState: (ttsState) => set({ ttsState }),
  setVadActive: (vadActive) => set({ vadActive }),
  setAudioLevel: (audioLevel) => set({ audioLevel }),
  setLastTranscript: (lastTranscript) => set({ lastTranscript }),
  setActivationMode: (activationMode) => set({ activationMode }),
  setWakeWordEnabled: (wakeWordEnabled) => set({ wakeWordEnabled }),
  setClapEnabled: (clapEnabled) => set({ clapEnabled }),
  setAlwaysOnEnabled: (alwaysOnEnabled) => set({ alwaysOnEnabled }),
}))
