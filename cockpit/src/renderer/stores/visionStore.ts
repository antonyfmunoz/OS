import { create } from 'zustand'

export type CameraStatus = 'off' | 'connecting' | 'live' | 'analyzing' | 'error'

export interface CameraPreset {
  label: string
  pan?: number
  tilt?: number
  zoom?: number
  mode?: 'physical_ptz' | 'digital_roi'
  analysis_hint?: string
}

export type AnalysisStatus = 'idle' | 'capturing' | 'analyzing' | 'complete' | 'error'

export type QualityMode = 'smooth' | 'balanced' | 'sharp' | 'analysis'

export interface QualityProfile {
  fps: number
  width: number
  height: number
  quality: number
  priority: string
}

export const QUALITY_PROFILES: Record<QualityMode, QualityProfile> = {
  smooth:   { fps: 30, width: 1280, height: 720,  quality: 55, priority: 'fps' },
  balanced: { fps: 15, width: 1280, height: 720,  quality: 70, priority: 'latency_quality' },
  sharp:    { fps: 10, width: 1920, height: 1080, quality: 80, priority: 'image_quality' },
  analysis: { fps: 1,  width: 1920, height: 1080, quality: 90, priority: 'ai_snapshot' },
}

export interface PtzPosition {
  pan: number
  tilt: number
  zoom: number
}

export interface StreamMetrics {
  actualFps: number
  targetFps: number
  avgFrameSize: number
  latencyMs: number
  droppedFrames: number
  lastFrameAge: number
}

// ── Tracking types ────────────────────────────────────────────────

export type TrackingStatus = 'visible' | 'likely_visible' | 'lost' | 'occluded' | 'moved' | 'stationary' | 'unknown'

export interface TrackedObjectState {
  track_id: string
  label: string
  description: string
  confidence: number
  status: TrackingStatus
  last_seen: number
  source: string
  operator_confirmed: boolean
}

export interface WatchItemState {
  watch_id: string
  target_label: string
  condition: string
  active: boolean
  expires_at: number
}

export interface FollowModeState {
  active: boolean
  target: string
  track_id: string
}

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

  qualityMode: QualityMode
  ptzPosition: PtzPosition
  ptzMoving: boolean
  hasPtzHardware: boolean
  streamMetrics: StreamMetrics

  // Tracking state
  detectedObjects: TrackedObjectState[]
  trackedObjects: TrackedObjectState[]
  labeledItems: TrackedObjectState[]
  activeWatches: WatchItemState[]
  followMode: FollowModeState
  sceneSummary: string
  sceneTimestamp: number
  sceneExpired: boolean

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

  setQualityMode: (mode: QualityMode) => void
  setPtzPosition: (pos: PtzPosition) => void
  setPtzMoving: (moving: boolean) => void
  setHasPtzHardware: (has: boolean) => void
  updateStreamMetrics: (partial: Partial<StreamMetrics>) => void

  // Tracking setters
  setDetectedObjects: (objects: TrackedObjectState[]) => void
  setTrackedObjects: (objects: TrackedObjectState[]) => void
  setLabeledItems: (items: TrackedObjectState[]) => void
  setActiveWatches: (watches: WatchItemState[]) => void
  setFollowMode: (follow: FollowModeState) => void
  setSceneSummary: (summary: string) => void
  setSceneTimestamp: (ts: number) => void
  setSceneExpired: (expired: boolean) => void
  updateSceneState: (state: Record<string, unknown>) => void

  reset: () => void
}

const INITIAL_METRICS: StreamMetrics = {
  actualFps: 0,
  targetFps: 0,
  avgFrameSize: 0,
  latencyMs: 0,
  droppedFrames: 0,
  lastFrameAge: 0,
}

const INITIAL_FOLLOW: FollowModeState = { active: false, target: '', track_id: '' }

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

  qualityMode: 'balanced',
  ptzPosition: { pan: 0, tilt: 0, zoom: 100 },
  ptzMoving: false,
  hasPtzHardware: true,
  streamMetrics: { ...INITIAL_METRICS },

  // Tracking initial state
  detectedObjects: [],
  trackedObjects: [],
  labeledItems: [],
  activeWatches: [],
  followMode: { ...INITIAL_FOLLOW },
  sceneSummary: '',
  sceneTimestamp: 0,
  sceneExpired: true,

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

  setQualityMode: (qualityMode) => set({ qualityMode }),
  setPtzPosition: (ptzPosition) => set({ ptzPosition }),
  setPtzMoving: (ptzMoving) => set({ ptzMoving }),
  setHasPtzHardware: (hasPtzHardware) => set({ hasPtzHardware }),
  updateStreamMetrics: (partial) => set((s) => ({
    streamMetrics: { ...s.streamMetrics, ...partial },
  })),

  // Tracking setters
  setDetectedObjects: (detectedObjects) => set({ detectedObjects }),
  setTrackedObjects: (trackedObjects) => set({ trackedObjects }),
  setLabeledItems: (labeledItems) => set({ labeledItems }),
  setActiveWatches: (activeWatches) => set({ activeWatches }),
  setFollowMode: (followMode) => set({ followMode }),
  setSceneSummary: (sceneSummary) => set({ sceneSummary }),
  setSceneTimestamp: (sceneTimestamp) => set({ sceneTimestamp }),
  setSceneExpired: (sceneExpired) => set({ sceneExpired }),
  updateSceneState: (state) => set({
    trackedObjects: (state.tracked_objects as TrackedObjectState[]) || [],
    labeledItems: (state.labeled_items as TrackedObjectState[]) || [],
    activeWatches: (state.active_watches as WatchItemState[]) || [],
    followMode: (state.follow_mode as FollowModeState) || { ...INITIAL_FOLLOW },
    sceneExpired: (state.scene_expired as boolean) ?? true,
    sceneTimestamp: (state.scene as Record<string, unknown>)?.timestamp as number || 0,
    sceneSummary: (state.scene as Record<string, unknown>)?.summary as string || '',
    detectedObjects: ((state.scene as Record<string, unknown>)?.objects as TrackedObjectState[]) || [],
  }),

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
    qualityMode: 'balanced',
    ptzPosition: { pan: 0, tilt: 0, zoom: 100 },
    ptzMoving: false,
    streamMetrics: { ...INITIAL_METRICS },
    detectedObjects: [],
    trackedObjects: [],
    labeledItems: [],
    activeWatches: [],
    followMode: { ...INITIAL_FOLLOW },
    sceneSummary: '',
    sceneTimestamp: 0,
    sceneExpired: true,
  }),
}))
