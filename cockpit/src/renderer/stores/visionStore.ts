import { create } from 'zustand'
import type { OverlayMetadata } from '../components/vision/VisionOverlay'

export type CameraStatus = 'off' | 'connecting' | 'live' | 'analyzing' | 'error'

export type CameraMode = 'manual' | 'follow' | 'watch' | 'ai_assist'

export type ControlAuthority = 'operator' | 'voice' | 'ai' | 'autonomous'

export interface AuthorityState {
  current: ControlAuthority
  aiEnabled: boolean
  aiIntentDescription: string
  lastOverrideAt: number
  lastOverrideBy: ControlAuthority
}

// ── Default-on policy ────────────────────────────────────────────

export type ProfileMode =
  | 'active_day' | 'deep_work' | 'creative_build'
  | 'admin_ops' | 'away' | 'night_cycle' | 'shutdown'

export interface CameraDefaultOnPolicy {
  enabled: boolean
  profileMode: ProfileMode
  operatorOverride: boolean
}

const DEFAULT_ON_BY_PROFILE: Record<ProfileMode, boolean> = {
  active_day: true,
  deep_work: false,
  creative_build: true,
  admin_ops: false,
  away: false,
  night_cycle: false,
  shutdown: false,
}

export function shouldAutoStartCamera(policy: CameraDefaultOnPolicy): boolean {
  if (!policy.enabled) return false
  if (policy.operatorOverride) return true
  return DEFAULT_ON_BY_PROFILE[policy.profileMode] ?? false
}

// ── Realtime PTZ motion state ────────────────────────────────────

export type MotionState =
  | 'idle' | 'moving' | 'stopping' | 'blocked' | 'disconnected'

export interface PtzMotionState {
  state: MotionState
  motionId: string
  panVelocity: number
  tiltVelocity: number
  zoomVelocity: number
  speed: number
  startedAt: number
}

// ── Control latency metrics ──────────────────────────────────────

export interface ControlMetrics {
  commandSendRate: number
  beastReceiveRate: number
  ptzLoopCadenceHz: number
  stopLatencyMs: number
  droppedCommands: number
  coalescedCommands: number
  guardTimeouts: number
  lastCommandSentAt: number
  lastStopSentAt: number
  lastStopAckedAt: number
}

export interface CameraPreset {
  id?: string
  label: string
  pan?: number
  tilt?: number
  zoom?: number
  mode?: 'physical_ptz' | 'digital_roi'
  device_id?: number
  analysis_hint?: string
  roi?: { x: number; y: number; zoom: number }
  created_at?: number
  updated_at?: number
}

export type DeviceStatus = 'usable' | 'busy' | 'stale' | 'unavailable' | 'duplicate' | 'error' | 'unknown'

export interface CameraDevice {
  index: number
  name: string
  physical_id: string
  raw_indexes: number[]
  width: number
  height: number
  fps: number
  status: DeviceStatus
  online: boolean
  busy: boolean
  selected: boolean
  last_validated_at: number
  last_probe_error: string | null
}

export type VisionReadiness = 'READY' | 'DEGRADED' | 'STALE' | 'OFFLINE' | 'BLOCKED'

export interface VisionReadinessState {
  readiness: VisionReadiness
  reason: string
  details: {
    beastConnected: boolean
    deviceValidated: boolean
    streamActive: boolean
    frameAge: number
    fpsOk: boolean
    commandPathReady: boolean
    ptzReady: boolean
    detectorReady: boolean
    presetsLoaded: boolean
  }
}

export function computeVisionReadiness(
  health: VisionHealthState,
  streaming: boolean,
  latestFrameAt: number | null,
  fps: number,
  hasPtzHardware: boolean,
  presetsLoaded: boolean,
): VisionReadinessState {
  const now = Date.now()
  const frameAge = latestFrameAt ? now - latestFrameAt : Infinity
  const fpsOk = fps > 0
  const deviceValidated = health.cameraAvailable || health.cameraStreaming
  const details = {
    beastConnected: health.beastConnected,
    deviceValidated,
    streamActive: streaming,
    frameAge: latestFrameAt ? frameAge : -1,
    fpsOk,
    commandPathReady: health.commandPathReady,
    ptzReady: hasPtzHardware || health.digitalRoiAvailable,
    detectorReady: health.detectorStatus?.loaded ?? false,
    presetsLoaded,
  }

  if (!health.beastConnected) return { readiness: 'OFFLINE', reason: 'Beast not connected', details }
  if (!health.relayRunning && !health.cockpitConnected) return { readiness: 'OFFLINE', reason: 'Relay offline', details }
  if (health.blockers.length > 0) return { readiness: 'BLOCKED', reason: health.blockers[0], details }
  if (!streaming) return { readiness: 'OFFLINE', reason: 'Stream not active', details }
  if (frameAge > 5000) return { readiness: 'STALE', reason: `No frames for ${Math.round(frameAge / 1000)}s`, details }
  if (frameAge > 2000) return { readiness: 'DEGRADED', reason: `Frame age ${Math.round(frameAge / 1000)}s`, details }
  if (!fpsOk) return { readiness: 'DEGRADED', reason: 'FPS dropped to 0', details }
  if (!health.commandPathReady) return { readiness: 'DEGRADED', reason: 'Command path not ready', details }
  return { readiness: 'READY', reason: 'All systems operational', details }
}

export type AnalysisStatus = 'idle' | 'capturing' | 'analyzing' | 'complete' | 'error'

export type QualityMode = 'smooth' | 'balanced' | 'high' | 'analysis'

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
  high:     { fps: 10, width: 1920, height: 1080, quality: 85, priority: 'image_quality' },
  analysis: { fps: 1,  width: 1920, height: 1080, quality: 95, priority: 'ai_snapshot' },
}

const QUALITY_STORAGE_KEY = 'umh_vision_quality_mode'

export function loadQualityModeFromStorage(): QualityMode {
  try {
    const raw = localStorage.getItem(QUALITY_STORAGE_KEY)
    if (raw && raw in QUALITY_PROFILES) return raw as QualityMode
  } catch { /* ignore */ }
  return 'balanced'
}

function saveQualityModeToStorage(mode: QualityMode): void {
  try { localStorage.setItem(QUALITY_STORAGE_KEY, mode) } catch { /* ignore */ }
}

export interface PtzPosition {
  pan: number
  tilt: number
  zoom: number
}

export type FrameFreshness = 'live' | 'recent' | 'stale' | 'dead' | 'none'

export function computeFrameFreshness(ageMs: number, hasFrame: boolean): FrameFreshness {
  if (!hasFrame) return 'none'
  if (ageMs < 2000) return 'live'
  if (ageMs < 5000) return 'recent'
  if (ageMs < 15000) return 'stale'
  return 'dead'
}

export interface StreamMetrics {
  actualFps: number
  targetFps: number
  avgFrameSize: number
  bitrateKbps: number
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

// ── Tracker stack types ──────────────────────────────────────────

export interface TrackerConfigState {
  tracker_id: string
  category: string
  enabled: boolean
  fps: number
  overlay: boolean
  cpu_cost: number
  gpu_cost: number
  status: string
  available: boolean
}

export interface TrackerStackState {
  active_stack_id: string
  enabled_trackers: TrackerConfigState[]
  total_cost: { cpu: number; gpu: number }
}

// ── Vision preset types ──────────────────────────────────────────

export interface VisionPresetInfo {
  preset_id: string
  label: string
  description: string
  ptz: { pan: number; tilt: number; zoom: number }
  tracker_stack_id: string
  quality_mode: string
  zones: Array<{ zone_id: string; label: string; polygon: number[][]; zone_type: string }>
  trigger_chain_ids: string[]
}

// ── Trigger chain types ──────────────────────────────────────────

export interface TriggerChainInfo {
  chain_id: string
  label: string
  enabled: boolean
  trigger: { event: string; zone: string; confidence_min: number; debounce_seconds: number }
  actions: Array<{ type: string; [key: string]: unknown }>
  governance: { risk: string; requires_approval: boolean; audit: boolean }
  fire_count: number
}

export interface ChainFireInfo {
  chain_id: string
  fired_at: number
  event: string
  confidence: number
  actions_taken: string[]
  explanation: string
}

// ── Security mode types ──────────────────────────────────────────

export interface SecurityModeInfo {
  active: boolean
  mode: string
  risk: string
  triggered_by: string
  started_at: number
  actions_taken: string[]
  requires_review: boolean
}

// ── Connection health types ──────────────────────────────────────

export type VisionChainStatus =
  | 'relay_offline'
  | 'authenticating'
  | 'connected_no_frames'
  | 'beast_offline'
  | 'camera_unavailable'
  | 'stream_stale'
  | 'healthy'
  | 'degraded'
  | 'relay_idle'

export interface DetectorStatus {
  source: string
  host: string
  model: string
  loaded: boolean
  inference_ms: number
  avg_inference_ms: number
  detection_frames: number
  tracker_active: boolean
  active_tracks: number
  total_tracks: number
  device?: string
}

export interface RoiState {
  x: number
  y: number
  zoom: number
}

export interface VisionHealthState {
  status: VisionChainStatus
  relayRunning: boolean
  cockpitConnected: boolean
  beastConnected: boolean
  cameraAvailable: boolean
  cameraStreaming: boolean
  lastFrameAt: number
  lastFrameAgeMs: number
  frameFps: number
  trackerRuntimeAvailable: boolean
  activeTrackers: string[]
  lastOverlayAt: number
  lastOverlayAgeMs: number
  triggerChainEngineAvailable: boolean
  activeChains: string[]
  securityMode: string
  detectorStatus: DetectorStatus | null
  blockers: string[]
  recoveryAction: string
  lastCheckedAt: number
  ptzMode: 'physical_ptz' | 'digital_roi'
  physicalPtzAvailable: boolean
  digitalRoiAvailable: boolean
  commandPathReady: boolean
  roi: RoiState
}

// ── Label correction types ──────────────────────────────────────

export interface LabelCorrection {
  correctedLabel: string
  rawLabel: string
  trackId: string
  correctedAt: number
}

// ── Toast notification types ────────────────────────────────────

export interface ToastNotification {
  id: string
  message: string
  variant: 'ok' | 'danger' | 'warning' | 'cyan'
  expiresAt: number
}

// ── Command latency measurement ─────────────────────────────────

export interface CommandLatencyMeasurement {
  commandId: string
  sentAt: number
  ackedAt: number
  roundTripMs: number
  operation: string
}

// ── Security notification types ─────────────────────────────────

export type NotificationSeverity = 'info' | 'warn' | 'critical'

export interface SecurityNotification {
  id: string
  severity: NotificationSeverity
  event: string
  source: string
  detail: string
  action: string
  timestamp: number
  acknowledged: boolean
  persistent: boolean
}

const NOTIFICATION_STORAGE_KEY = 'umh_security_notifications'

function loadNotificationsFromStorage(): SecurityNotification[] {
  try {
    const raw = localStorage.getItem(NOTIFICATION_STORAGE_KEY)
    if (raw) {
      const all = JSON.parse(raw) as SecurityNotification[]
      return all.filter((n) => n.persistent || Date.now() - n.timestamp < 86400000)
    }
  } catch { /* ignore */ }
  return []
}

function saveNotificationsToStorage(notifications: SecurityNotification[]): void {
  try {
    const persistent = notifications.filter((n) => n.persistent || Date.now() - n.timestamp < 86400000)
    localStorage.setItem(NOTIFICATION_STORAGE_KEY, JSON.stringify(persistent.slice(-200)))
  } catch { /* ignore */ }
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

  // Camera devices
  cameraDevices: CameraDevice[]
  selectedDeviceIndex: number
  deviceScanLoading: boolean
  settingsOpen: boolean

  // Connection health
  chainHealth: VisionHealthState

  // Tracking state
  detectedObjects: TrackedObjectState[]
  trackedObjects: TrackedObjectState[]
  labeledItems: TrackedObjectState[]
  activeWatches: WatchItemState[]
  followMode: FollowModeState
  sceneSummary: string
  sceneTimestamp: number
  sceneExpired: boolean

  // Tracker stack state
  trackerStack: TrackerStackState
  // Vision presets (CRUD presets, not camera presets)
  visionPresets: Record<string, VisionPresetInfo>
  activeVisionPresetId: string
  // Trigger chains
  triggerChains: Record<string, TriggerChainInfo>
  recentFires: ChainFireInfo[]
  lastChainExplanation: string
  // Security mode
  securityMode: SecurityModeInfo

  // Label corrections — operator overrides for detector labels
  labelCorrections: Record<string, LabelCorrection>

  // Toast notifications
  toasts: ToastNotification[]

  // Command latency history
  latencyHistory: CommandLatencyMeasurement[]

  // Security notifications
  notifications: SecurityNotification[]
  notificationUnreadCount: number

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

  // Camera device setters
  setCameraDevices: (devices: CameraDevice[]) => void
  setSelectedDeviceIndex: (index: number) => void
  setDeviceScanLoading: (loading: boolean) => void
  setSettingsOpen: (open: boolean) => void
  deviceSwitching: boolean
  deviceSwitchError: string | null
  setDeviceSwitching: (switching: boolean) => void
  setDeviceSwitchError: (error: string | null) => void

  // Connection health setters
  updateChainHealth: (health: Partial<VisionHealthState>) => void

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

  // Tracker stack setters
  updateTrackerStack: (state: Partial<TrackerStackState>) => void
  // Preset setters
  setVisionPresets: (presets: Record<string, VisionPresetInfo>) => void
  setActiveVisionPresetId: (id: string) => void
  // Chain setters
  setTriggerChains: (chains: Record<string, TriggerChainInfo>) => void
  setRecentFires: (fires: ChainFireInfo[]) => void
  setLastChainExplanation: (explanation: string) => void
  // Security mode setters
  setSecurityMode: (mode: Partial<SecurityModeInfo>) => void

  // Label correction setters
  setLabelCorrection: (trackId: string, correctedLabel: string, rawLabel: string) => void
  removeLabelCorrection: (trackId: string) => void
  mergeLabelCorrections: (beastCorrections: Record<string, string>) => void
  getEffectiveLabel: (trackId: string, rawLabel: string) => string
  loadLabelCorrections: () => void

  // Toast setters
  addToast: (message: string, variant: ToastNotification['variant']) => void
  removeToast: (id: string) => void

  // Latency setters
  recordLatency: (measurement: CommandLatencyMeasurement) => void

  // Security notification setters
  addNotification: (severity: NotificationSeverity, event: string, source: string, detail: string, action?: string, persistent?: boolean) => void
  acknowledgeNotification: (id: string) => void
  clearNotification: (id: string) => void
  clearAllNotifications: () => void

  // Overlay data (from vision_overlay WS events)
  overlays: OverlayMetadata[]
  setOverlays: (overlays: OverlayMetadata[]) => void
  diagnosticOverlay: boolean
  setDiagnosticOverlay: (enabled: boolean) => void
  overlayVisible: boolean
  setOverlayVisible: (visible: boolean) => void

  // Default-on policy
  defaultOnPolicy: CameraDefaultOnPolicy
  setDefaultOnPolicy: (policy: Partial<CameraDefaultOnPolicy>) => void

  // Realtime PTZ motion state
  ptzMotion: PtzMotionState
  setPtzMotion: (motion: Partial<PtzMotionState>) => void

  // Control latency metrics
  controlMetrics: ControlMetrics
  updateControlMetrics: (partial: Partial<ControlMetrics>) => void

  // Session management
  viewerCount: number
  cameraSessionActive: boolean
  setViewerCount: (count: number) => void
  setCameraSessionActive: (active: boolean) => void

  // Camera mode
  cameraMode: CameraMode
  setCameraMode: (mode: CameraMode) => void

  // Authority state
  authority: AuthorityState
  setAuthority: (partial: Partial<AuthorityState>) => void
  claimAuthority: (who: ControlAuthority, reason?: string) => void

  // Preset loading state
  presetsLoading: boolean
  presetsLoadError: string | null
  presetsLoadedAt: number
  setPresetsLoading: (loading: boolean) => void
  setPresetsLoadError: (error: string | null) => void

  reset: () => void
}

const INITIAL_METRICS: StreamMetrics = {
  actualFps: 0,
  targetFps: 0,
  avgFrameSize: 0,
  bitrateKbps: 0,
  latencyMs: 0,
  droppedFrames: 0,
  lastFrameAge: 0,
}

const INITIAL_FOLLOW: FollowModeState = { active: false, target: '', track_id: '' }
const INITIAL_TRACKER_STACK: TrackerStackState = { active_stack_id: '', enabled_trackers: [], total_cost: { cpu: 0, gpu: 0 } }
const INITIAL_SECURITY: SecurityModeInfo = { active: false, mode: 'normal', risk: 'low', triggered_by: '', started_at: 0, actions_taken: [], requires_review: false }
const INITIAL_DEFAULT_ON: CameraDefaultOnPolicy = {
  enabled: true,
  profileMode: 'active_day',
  operatorOverride: false,
}
const INITIAL_PTZ_MOTION: PtzMotionState = {
  state: 'idle',
  motionId: '',
  panVelocity: 0,
  tiltVelocity: 0,
  zoomVelocity: 0,
  speed: 1,
  startedAt: 0,
}
const INITIAL_AUTHORITY: AuthorityState = {
  current: 'operator',
  aiEnabled: false,
  aiIntentDescription: '',
  lastOverrideAt: 0,
  lastOverrideBy: 'operator',
}

const INITIAL_CONTROL_METRICS: ControlMetrics = {
  commandSendRate: 0,
  beastReceiveRate: 0,
  ptzLoopCadenceHz: 0,
  stopLatencyMs: 0,
  droppedCommands: 0,
  coalescedCommands: 0,
  guardTimeouts: 0,
  lastCommandSentAt: 0,
  lastStopSentAt: 0,
  lastStopAckedAt: 0,
}
const INITIAL_HEALTH: VisionHealthState = {
  status: 'relay_offline',
  relayRunning: false,
  cockpitConnected: false,
  beastConnected: false,
  cameraAvailable: false,
  cameraStreaming: false,
  lastFrameAt: 0,
  lastFrameAgeMs: -1,
  frameFps: 0,
  trackerRuntimeAvailable: false,
  activeTrackers: [],
  lastOverlayAt: 0,
  lastOverlayAgeMs: -1,
  triggerChainEngineAvailable: false,
  activeChains: [],
  securityMode: 'normal',
  detectorStatus: null,
  blockers: [],
  recoveryAction: '',
  lastCheckedAt: 0,
  ptzMode: 'physical_ptz',
  physicalPtzAvailable: false,
  digitalRoiAvailable: true,
  commandPathReady: false,
  roi: { x: 0, y: 0, zoom: 1 },
}

const LABEL_CORRECTIONS_KEY = 'umh_vision_label_corrections'
const PRESET_STORAGE_KEY = 'umh_vision_presets'

function loadCorrectionsFromStorage(): Record<string, LabelCorrection> {
  try {
    const raw = localStorage.getItem(LABEL_CORRECTIONS_KEY)
    if (raw) return JSON.parse(raw) as Record<string, LabelCorrection>
  } catch { /* ignore */ }
  return {}
}

function saveCorrectionsToStorage(corrections: Record<string, LabelCorrection>): void {
  try {
    localStorage.setItem(LABEL_CORRECTIONS_KEY, JSON.stringify(corrections))
  } catch { /* ignore */ }
}

export function loadPresetsFromStorage(): Record<string, CameraPreset> {
  try {
    const raw = localStorage.getItem(PRESET_STORAGE_KEY)
    if (raw) return JSON.parse(raw) as Record<string, CameraPreset>
  } catch { /* ignore */ }
  return {}
}

export function savePresetsToStorage(presets: Record<string, CameraPreset>): void {
  try {
    localStorage.setItem(PRESET_STORAGE_KEY, JSON.stringify(presets))
  } catch { /* ignore */ }
}

let _toastId = 0

export const useVisionStore = create<VisionState>((set, get) => ({
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

  qualityMode: loadQualityModeFromStorage(),
  ptzPosition: { pan: 0, tilt: 0, zoom: 100 },
  ptzMoving: false,
  hasPtzHardware: true,
  streamMetrics: { ...INITIAL_METRICS },

  // Camera devices
  cameraDevices: [],
  selectedDeviceIndex: 0,
  deviceScanLoading: false,
  settingsOpen: false,

  // Connection health initial state
  chainHealth: { ...INITIAL_HEALTH },

  // Tracking initial state
  detectedObjects: [],
  trackedObjects: [],
  labeledItems: [],
  activeWatches: [],
  followMode: { ...INITIAL_FOLLOW },
  sceneSummary: '',
  sceneTimestamp: 0,
  sceneExpired: true,

  // Tracker stack initial state
  trackerStack: { ...INITIAL_TRACKER_STACK },
  // Vision presets initial state
  visionPresets: {},
  activeVisionPresetId: '',
  // Trigger chains initial state
  triggerChains: {},
  recentFires: [],
  lastChainExplanation: '',
  // Security mode initial state
  securityMode: { ...INITIAL_SECURITY },

  // Label corrections
  labelCorrections: loadCorrectionsFromStorage(),
  // Toasts
  toasts: [],
  // Command latency history (keep last 20)
  latencyHistory: [],
  // Security notifications
  notifications: loadNotificationsFromStorage(),
  notificationUnreadCount: loadNotificationsFromStorage().filter((n) => !n.acknowledged).length,

  setConnected: (connected) => set({ connected }),
  setStreaming: (streaming) => set({ streaming }),
  setCameraStatus: (cameraStatus) => set({ cameraStatus }),
  setActivePreset: (activePreset) => set({ activePreset }),
  setLatestFrame: (url, timestamp) => set({ latestFrameUrl: url, latestFrameAt: timestamp }),
  clearFrame: () => set({ latestFrameUrl: null, latestFrameAt: null }),
  setError: (error) => set({ error }),
  setPresets: (presets) => {
    const merged = { ...loadPresetsFromStorage(), ...presets }
    savePresetsToStorage(merged)
    set({ presets: merged })
  },
  setAnalysisStatus: (analysisStatus) => set({ analysisStatus }),
  setAnalysisResult: (analysisResult) => set({ analysisResult }),
  incrementFrameCount: () => set((s) => ({ frameCount: s.frameCount + 1 })),
  setPoppedOut: (poppedOut, win) => set({ poppedOut, popoutWindow: win ?? null }),

  setQualityMode: (qualityMode) => { saveQualityModeToStorage(qualityMode); set({ qualityMode }) },
  setPtzPosition: (ptzPosition) => set({ ptzPosition }),
  setPtzMoving: (ptzMoving) => set({ ptzMoving }),
  setHasPtzHardware: (hasPtzHardware) => set({ hasPtzHardware }),
  updateStreamMetrics: (partial) => set((s) => ({
    streamMetrics: { ...s.streamMetrics, ...partial },
  })),

  // Camera device setters
  setCameraDevices: (cameraDevices) => set({ cameraDevices }),
  setSelectedDeviceIndex: (selectedDeviceIndex) => set({ selectedDeviceIndex }),
  setDeviceScanLoading: (deviceScanLoading) => set({ deviceScanLoading }),
  setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
  deviceSwitching: false,
  deviceSwitchError: null,
  setDeviceSwitching: (deviceSwitching) => set({ deviceSwitching }),
  setDeviceSwitchError: (deviceSwitchError) => set({ deviceSwitchError }),

  // Connection health setter
  updateChainHealth: (partial) => set((s) => ({
    chainHealth: { ...s.chainHealth, ...partial, lastCheckedAt: Date.now() },
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

  // Tracker stack setters
  updateTrackerStack: (partial) => set((s) => ({
    trackerStack: { ...s.trackerStack, ...partial },
  })),
  // Preset setters
  setVisionPresets: (visionPresets) => set({ visionPresets }),
  setActiveVisionPresetId: (activeVisionPresetId) => set({ activeVisionPresetId }),
  // Chain setters
  setTriggerChains: (triggerChains) => set({ triggerChains }),
  setRecentFires: (recentFires) => set({ recentFires }),
  setLastChainExplanation: (lastChainExplanation) => set({ lastChainExplanation }),
  // Security mode setters
  setSecurityMode: (partial) => set((s) => ({
    securityMode: { ...s.securityMode, ...partial },
  })),

  // Label correction setters
  setLabelCorrection: (trackId, correctedLabel, rawLabel) => set((s) => {
    const corrections = {
      ...s.labelCorrections,
      [trackId]: { correctedLabel, rawLabel, trackId, correctedAt: Date.now() },
    }
    saveCorrectionsToStorage(corrections)
    return { labelCorrections: corrections }
  }),
  removeLabelCorrection: (trackId) => set((s) => {
    const corrections = { ...s.labelCorrections }
    delete corrections[trackId]
    saveCorrectionsToStorage(corrections)
    return { labelCorrections: corrections }
  }),
  mergeLabelCorrections: (beastCorrections) => set((s) => {
    let changed = false
    const corrections = { ...s.labelCorrections }
    for (const [trackId, correctedLabel] of Object.entries(beastCorrections)) {
      if (!corrections[trackId]) {
        corrections[trackId] = { correctedLabel, rawLabel: correctedLabel, trackId, correctedAt: Date.now() }
        changed = true
      }
    }
    if (!changed) return s
    saveCorrectionsToStorage(corrections)
    return { labelCorrections: corrections }
  }),
  getEffectiveLabel: (trackId, rawLabel) => {
    const correction = get().labelCorrections[trackId]
    return correction ? correction.correctedLabel : rawLabel
  },
  loadLabelCorrections: () => set({ labelCorrections: loadCorrectionsFromStorage() }),

  // Toast setters
  addToast: (message, variant) => set((s) => {
    const id = `toast_${++_toastId}`
    const toast: ToastNotification = { id, message, variant, expiresAt: Date.now() + 4000 }
    return { toasts: [...s.toasts, toast] }
  }),
  removeToast: (id) => set((s) => ({
    toasts: s.toasts.filter((t) => t.id !== id),
  })),

  // Latency recording
  recordLatency: (measurement) => set((s) => ({
    latencyHistory: [...s.latencyHistory.slice(-19), measurement],
  })),

  // Security notification setters
  addNotification: (severity, event, source, detail, action = '', persistent = false) => set((s) => {
    const id = `notif_${++_toastId}`
    const n: SecurityNotification = { id, severity, event, source, detail, action, timestamp: Date.now(), acknowledged: false, persistent: severity === 'critical' || persistent }
    const notifications = [...s.notifications, n].slice(-200)
    const unread = notifications.filter((x) => !x.acknowledged).length
    saveNotificationsToStorage(notifications)
    return { notifications, notificationUnreadCount: unread }
  }),
  acknowledgeNotification: (id) => set((s) => {
    const notifications = s.notifications.map((n) => n.id === id ? { ...n, acknowledged: true } : n)
    const unread = notifications.filter((n) => !n.acknowledged).length
    saveNotificationsToStorage(notifications)
    return { notifications, notificationUnreadCount: unread }
  }),
  clearNotification: (id) => set((s) => {
    const notifications = s.notifications.filter((n) => n.id !== id)
    const unread = notifications.filter((n) => !n.acknowledged).length
    saveNotificationsToStorage(notifications)
    return { notifications, notificationUnreadCount: unread }
  }),
  clearAllNotifications: () => {
    saveNotificationsToStorage([])
    set({ notifications: [], notificationUnreadCount: 0 })
  },

  // Overlay data
  overlays: [],
  setOverlays: (overlays) => set({ overlays }),
  diagnosticOverlay: false,
  setDiagnosticOverlay: (diagnosticOverlay) => set({ diagnosticOverlay }),
  overlayVisible: true,
  setOverlayVisible: (overlayVisible) => set({ overlayVisible }),

  // Default-on policy
  defaultOnPolicy: { ...INITIAL_DEFAULT_ON },
  setDefaultOnPolicy: (partial) => set((s) => ({
    defaultOnPolicy: { ...s.defaultOnPolicy, ...partial },
  })),

  // Realtime PTZ motion state
  ptzMotion: { ...INITIAL_PTZ_MOTION },
  setPtzMotion: (partial) => set((s) => ({
    ptzMotion: { ...s.ptzMotion, ...partial },
  })),

  // Control latency metrics
  controlMetrics: { ...INITIAL_CONTROL_METRICS },
  updateControlMetrics: (partial) => set((s) => ({
    controlMetrics: { ...s.controlMetrics, ...partial },
  })),

  // Session management
  viewerCount: 0,
  cameraSessionActive: false,
  setViewerCount: (viewerCount) => set({ viewerCount }),
  setCameraSessionActive: (cameraSessionActive) => set({ cameraSessionActive }),

  // Camera mode
  cameraMode: 'manual',
  setCameraMode: (cameraMode) => set({ cameraMode }),

  // Authority state
  authority: { ...INITIAL_AUTHORITY },
  setAuthority: (partial) => set((s) => ({
    authority: { ...s.authority, ...partial },
  })),
  claimAuthority: (who, reason) => set((s) => {
    const prev = s.authority.current
    if (prev === who) return s
    return {
      authority: {
        ...s.authority,
        current: who,
        lastOverrideAt: Date.now(),
        lastOverrideBy: prev,
        aiIntentDescription: reason || '',
      },
    }
  }),

  // Preset loading state
  presetsLoading: false,
  presetsLoadError: null,
  presetsLoadedAt: 0,
  setPresetsLoading: (presetsLoading) => set({ presetsLoading }),
  setPresetsLoadError: (presetsLoadError) => set({ presetsLoadError }),

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
    qualityMode: loadQualityModeFromStorage(),
    ptzPosition: { pan: 0, tilt: 0, zoom: 100 },
    ptzMoving: false,
    streamMetrics: { ...INITIAL_METRICS },
    chainHealth: { ...INITIAL_HEALTH },
    detectedObjects: [],
    trackedObjects: [],
    labeledItems: [],
    activeWatches: [],
    followMode: { ...INITIAL_FOLLOW },
    sceneSummary: '',
    sceneTimestamp: 0,
    sceneExpired: true,
    trackerStack: { ...INITIAL_TRACKER_STACK },
    visionPresets: {},
    activeVisionPresetId: '',
    triggerChains: {},
    recentFires: [],
    lastChainExplanation: '',
    securityMode: { ...INITIAL_SECURITY },
    labelCorrections: loadCorrectionsFromStorage(),
    toasts: [],
    latencyHistory: [],
    notifications: loadNotificationsFromStorage(),
    notificationUnreadCount: loadNotificationsFromStorage().filter((n) => !n.acknowledged).length,
    overlays: [],
    diagnosticOverlay: false,
    overlayVisible: true,
    defaultOnPolicy: { ...INITIAL_DEFAULT_ON },
    ptzMotion: { ...INITIAL_PTZ_MOTION },
    controlMetrics: { ...INITIAL_CONTROL_METRICS },
    viewerCount: 0,
    cameraSessionActive: false,
    cameraMode: 'manual',
    authority: { ...INITIAL_AUTHORITY },
    presetsLoading: false,
    presetsLoadError: null,
    presetsLoadedAt: 0,
  }),
}))
