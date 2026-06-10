import { create } from 'zustand'

export type CameraStatus = 'off' | 'connecting' | 'live' | 'analyzing' | 'error'

export interface CameraPreset {
  label: string
  pan?: number
  tilt?: number
  zoom?: number
  analysis_hint?: string
}

export type AnalysisStatus = 'idle' | 'capturing' | 'analyzing' | 'complete' | 'error'

interface VisionState {
  connected: boolean
  streaming: boolean
  cameraStatus: CameraStatus
  activeNodeId: string
  activeCameraId: string
  activePreset: string
  latestFrameUrl: string | null
  latestFrameAt: number | null
  fps: number
  width: number
  height: number
  error: string | null
  presets: Record<string, CameraPreset>
  analysisStatus: AnalysisStatus
  analysisResult: string | null
  frameCount: number
  poppedOut: boolean
  popoutWindow: Window | null

  setConnected: (connected: boolean) => void
  setStreaming: (streaming: boolean) => void
  setCameraStatus: (status: CameraStatus) => void
  setActivePreset: (preset: string) => void
  setLatestFrame: (url: string, timestamp: number) => void
  clearFrame: () => void
  setError: (error: string | null) => void
  setPresets: (presets: Record<string, CameraPreset>) => void
  setAnalysisStatus: (status: AnalysisStatus) => void
  setAnalysisResult: (result: string | null) => void
  incrementFrameCount: () => void
  setPoppedOut: (poppedOut: boolean, win?: Window | null) => void
  reset: () => void
}

export const useVisionStore = create<VisionState>((set) => ({
  connected: false,
  streaming: false,
  cameraStatus: 'off',
  activeNodeId: '',
  activeCameraId: 'default',
  activePreset: '',
  latestFrameUrl: null,
  latestFrameAt: null,
  fps: 0,
  width: 0,
  height: 0,
  error: null,
  presets: {},
  analysisStatus: 'idle',
  analysisResult: null,
  frameCount: 0,
  poppedOut: false,
  popoutWindow: null,

  setConnected: (connected) => set({ connected }),
  setStreaming: (streaming) => set({ streaming }),
  setCameraStatus: (cameraStatus) => set({ cameraStatus }),
  setActivePreset: (activePreset) => set({ activePreset }),
  setLatestFrame: (url, timestamp) => set({ latestFrameUrl: url, latestFrameAt: timestamp }),
  clearFrame: () => set({ latestFrameUrl: null, latestFrameAt: null }),
  setError: (error) => set({ error }),
  setPresets: (presets) => set({ presets }),
  setAnalysisStatus: (analysisStatus) => set({ analysisStatus }),
  setAnalysisResult: (analysisResult) => set({ analysisResult }),
  incrementFrameCount: () => set((s) => ({ frameCount: s.frameCount + 1 })),
  setPoppedOut: (poppedOut, win) => set({ poppedOut, popoutWindow: win ?? null }),
  reset: () => set({
    connected: false,
    streaming: false,
    cameraStatus: 'off',
    activePreset: '',
    latestFrameUrl: null,
    latestFrameAt: null,
    error: null,
    analysisStatus: 'idle',
    analysisResult: null,
    frameCount: 0,
    poppedOut: false,
    popoutWindow: null,
  }),
}))
