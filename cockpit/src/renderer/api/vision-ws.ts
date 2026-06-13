import { WsClient } from './websocket'

function getVisionUrl(): string {
  if (import.meta.env.VITE_VISION_URL) return import.meta.env.VITE_VISION_URL as string

  const isLocalhost =
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
  const isElectron = Boolean((window as Record<string, unknown>).cockpit)

  if (isElectron || isLocalhost) {
    return 'ws://localhost:8097/vision'
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/umh/vision/ws`
}

const VISION_URL = getVisionUrl()

const log = (stage: string, ...args: unknown[]) =>
  console.log(`[VisionPipeline] ${stage}`, ...args)

log('vision_ws_url_resolved', VISION_URL)

export interface CameraPreset {
  label: string
  pan?: number
  tilt?: number
  zoom?: number
  mode?: 'physical_ptz' | 'digital_roi'
  analysis_hint?: string
}

export type PtzDirection =
  | 'up' | 'down' | 'left' | 'right'
  | 'up_left' | 'up_right' | 'down_left' | 'down_right'

export interface TrackedObject {
  track_id: string
  label: string
  description: string
  confidence: number
  status: 'visible' | 'likely_visible' | 'lost' | 'occluded' | 'moved' | 'stationary' | 'unknown'
  last_seen: number
  source: string
  operator_confirmed: boolean
}

export interface WatchItem {
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

export interface SceneState {
  scene_id: string
  timestamp: number
  objects: TrackedObject[]
  summary: string
  vlm_analyzed: boolean
  scene_expired: boolean
  tracked_objects: TrackedObject[]
  labeled_items: TrackedObject[]
  active_watches: WatchItem[]
  follow_mode: FollowModeState
}

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

export interface VisionPresetState {
  preset_id: string
  label: string
  description: string
  ptz: { pan: number; tilt: number; zoom: number }
  tracker_stack_id: string
  quality_mode: string
  zones: Array<{ zone_id: string; label: string; polygon: number[][]; zone_type: string }>
  trigger_chain_ids: string[]
}

export interface TriggerChainState {
  chain_id: string
  label: string
  enabled: boolean
  trigger: { event: string; zone: string; confidence_min: number; debounce_seconds: number }
  actions: Array<{ type: string; [key: string]: unknown }>
  governance: { risk: string; requires_approval: boolean; audit: boolean }
  fire_count: number
}

export interface ChainFireState {
  chain_id: string
  fired_at: number
  event: string
  confidence: number
  actions_taken: string[]
  explanation: string
}

export type VisionEvent =
  | { type: 'connected' }
  | { type: 'disconnected' }
  | { type: 'vision_status'; streaming: boolean; source: string }
  | { type: 'vision_frame'; url: string; timestamp: number; byteLength: number }
  | { type: 'vision_snapshot'; image_base64: string; width: number; height: number }
  | { type: 'camera_presets'; presets: Record<string, CameraPreset> }
  | { type: 'camera_position'; pan: number; tilt: number; zoom: number; has_ptz_hardware: boolean }
  | { type: 'camera_control_result'; request_id: string; operation: string; ok: boolean; data: Record<string, unknown> }
  | { type: 'vision_error'; error: string }
  | { type: 'preset_saved'; preset: string }
  | { type: 'vision_scene_state'; [key: string]: unknown }
  | { type: 'vision_analysis_result'; answer: string; confidence: string; source: string }
  | { type: 'vision_track_result'; success: boolean; track_id?: string; label?: string; status?: string }
  | { type: 'vision_label_result'; success: boolean; track_id?: string; label?: string }
  | { type: 'vision_watch_result'; success: boolean; watch_id?: string; target?: string }
  | { type: 'vision_follow_result'; success: boolean; target?: string }
  | { type: 'vision_query_result'; answer: string; confidence: string; status?: string }
  | { type: 'vision_tracker_result'; success: boolean; category?: string; operation?: string; enabled?: string[]; error?: string }
  | { type: 'vision_tracker_state'; active_stack_id?: string; enabled_trackers?: TrackerConfigState[]; total_cost?: { cpu: number; gpu: number }; [key: string]: unknown }
  | { type: 'vision_preset_result'; success: boolean; preset_id?: string; label?: string; error?: string; affected_chains?: string[] }
  | { type: 'vision_preset_state'; active_preset_id?: string; presets?: Record<string, VisionPresetState>; count?: number }
  | { type: 'vision_chain_result'; success: boolean; chain_id?: string; label?: string; error?: string }
  | { type: 'vision_chain_explain'; explanation: string }
  | { type: 'vision_chain_state'; chains?: Record<string, TriggerChainState>; chain_count?: number; enabled_count?: number; recent_fires?: ChainFireState[] }
  | { type: 'vision_security_result'; success: boolean; mode?: string; active?: boolean; error?: string; [key: string]: unknown }
  | { type: 'vision_security_state'; active?: boolean; mode?: string; risk?: string; triggered_by?: string; [key: string]: unknown }
  | { type: 'vision_health'; status: string; blockers?: string[]; recovery_action?: string; [key: string]: unknown }
  | { type: 'ptz_motion_state'; motion_id: string; state: string; pan_velocity: number; tilt_velocity: number; zoom_velocity: number; loop_cadence_hz?: number; guard_timeout_events?: number }
  | { type: 'ptz_motion_ack'; motion_id: string; operation: string; ok: boolean }
  | { type: 'camera_session_state'; active: boolean; viewer_count: number }
  | { type: 'vision_overlay'; overlays: Array<{ type: string; track_id: string; label: string; confidence: number; bbox: { x: number; y: number; w: number; h: number }; landmarks?: Array<{ x: number; y: number; label?: string }>; connections?: Array<[number, number]>; color?: string }> }
  | { type: 'label_corrections_list'; corrections: Record<string, string> }
  | { type: 'vision_events'; events: Array<{ seq: number; type: string; timestamp: number; detail?: Record<string, unknown> }>; total: number }
  | { type: 'command_log'; commands: Array<{ id: number; operation: string; sent_at: number; rtt_ms: number; success: boolean; error?: string }>; total: number; ok: number; fail: number }
  | { type: 'fault_inject_ack'; fault?: string; active?: boolean; error?: string; faults: Record<string, boolean> }
  | { type: 'fault_status'; faults: Record<string, boolean> }
  | { type: 'authority_state'; current: string; accepted?: boolean; log: Array<{ at: number; from: string; to: string; reason: string }> }
  | { type: 'pipeline_metrics'; measured_fps: number; avg_ingest_ms: number; avg_broadcast_ms: number; p95_ingest_ms: number; avg_frame_bytes: number; avg_jitter_ms: number; max_jitter_ms: number; samples: number }
  | { type: 'camera_registry'; cameras: Record<string, unknown>; active: string }

function getVisionProtocols(): string[] {
  const token = import.meta.env.VITE_VISION_TOKEN as string | undefined
  if (token) return [`auth.${token}`]
  return []
}

let _requestId = 0
function nextRequestId(): string {
  return `vr_${++_requestId}_${Date.now()}`
}

export class VisionWsClient {
  private ws: WsClient
  private _prevBlobUrl: string | null = null
  private _latestFrameUrl: string | null = null
  private _frameCount = 0
  private _frameSizes: number[] = []
  private _fpsWindow: number[] = []
  private _pendingFrame: ArrayBuffer | null = null
  private _rafId: number | null = null

  constructor() {
    this.ws = new WsClient(VISION_URL, getVisionProtocols())
    this.ws.onBinary((buf) => this._enqueueFrame(buf))
  }

  connect(): Promise<void> {
    log('ws_connect', VISION_URL)
    return new Promise<void>((resolve) => {
      const onConnected = this.ws.on('connected', () => {
        log('ws_connected')
        onConnected()
        clearTimeout(timer)
        resolve()
      })
      const timer = setTimeout(() => {
        onConnected()
        log('ws_connect_timeout', '10s elapsed — WsClient continues reconnecting')
        resolve()
      }, 10000)
      this.ws.connect()
    })
  }

  disconnect(): void {
    log('disconnect')
    this._revokeFrame()
    this.ws.disconnect()
  }

  reconnect(): void {
    log('reconnect')
    this.ws.disconnect()
    setTimeout(() => {
      this.ws = new WsClient(VISION_URL, getVisionProtocols())
      // CRITICAL: re-register binary frame handler after replacing WsClient instance
      // Without this, video frames are silently dropped after reconnect()
      this.ws.onBinary((buf) => this._enqueueFrame(buf))
      this.ws.connect()
    }, 500)
  }

  restartCamera(opts: { fps?: number; width?: number; height?: number; quality?: number } = {}): void {
    log('restart_camera', opts)
    this.ws.send('camera_stop')
    setTimeout(() => {
      this.ws.send('camera_start', {
        fps: opts.fps ?? 15,
        width: opts.width ?? 640,
        height: opts.height ?? 480,
        quality: opts.quality ?? 65,
      })
      this.ws.send('vision_subscribe', { fps: opts.fps ?? 15, quality: opts.quality ?? 65 })
    }, 1000)
  }

  refreshCapabilities(): void {
    log('refresh_capabilities')
    this.ws.send('vision_tracker_state')
    this.ws.send('vision_health')
  }

  get connected(): boolean {
    return this.ws.connected
  }

  get latestFrameUrl(): string | null {
    return this._latestFrameUrl
  }

  get frameCount(): number {
    return this._frameCount
  }

  get measuredFps(): number {
    const now = Date.now()
    const window = this._fpsWindow.filter((t) => now - t < 2000)
    this._fpsWindow = window
    if (window.length < 2) return 0
    return Math.round((window.length / 2) * 10) / 10
  }

  get avgFrameSize(): number {
    if (this._frameSizes.length === 0) return 0
    const sum = this._frameSizes.reduce((a, b) => a + b, 0)
    return Math.round(sum / this._frameSizes.length)
  }

  // ── Camera control ──────────────────────────────────────────────

  listDevices(): void {
    log('camera_list_devices')
    this.ws.send('camera_list_devices', { request_id: nextRequestId() })
  }

  selectDevice(deviceIndex: number, opts?: { fps?: number; width?: number; height?: number; quality?: number }): void {
    log('camera_select_device', { device_index: deviceIndex, ...opts })
    this.ws.send('camera_select_device', {
      device_index: deviceIndex,
      fps: opts?.fps,
      width: opts?.width,
      height: opts?.height,
      quality: opts?.quality,
      request_id: nextRequestId(),
    })
  }

  startCamera(opts: { fps?: number; width?: number; height?: number; quality?: number } = {}): void {
    log('camera_start', opts)
    this.ws.send('camera_start', {
      fps: opts.fps ?? 2,
      width: opts.width ?? 640,
      height: opts.height ?? 480,
      quality: opts.quality ?? 60,
    })
  }

  stopCamera(): void {
    log('camera_stop')
    this.ws.send('camera_stop')
  }

  subscribe(fps = 2, quality = 60): void {
    log('vision_subscribe', { fps, quality })
    this.ws.send('vision_subscribe', { fps, quality })
  }

  unsubscribe(): void {
    log('vision_unsubscribe')
    this.ws.send('vision_unsubscribe')
  }

  setPreset(preset: string, smooth = false, duration = 1.0): void {
    log('camera_preset', { preset, smooth })
    this.ws.send('camera_preset', { preset, smooth, duration, request_id: nextRequestId() })
  }

  savePreset(preset: string, label: string, opts: { pan?: number; tilt?: number; zoom?: number; mode?: string; analysisHint?: string } = {}): void {
    log('camera_save_preset', { preset, label, ...opts })
    this.ws.send('camera_save_preset', {
      preset,
      label,
      pan: opts.pan,
      tilt: opts.tilt,
      zoom: opts.zoom,
      mode: opts.mode ?? 'physical_ptz',
      analysis_hint: opts.analysisHint ?? '',
      request_id: nextRequestId(),
    })
  }

  deletePresetOnDevice(preset: string): void {
    log('camera_delete_preset', { preset })
    this.ws.send('camera_delete_preset', { preset, request_id: nextRequestId() })
  }

  correctLabel(trackId: string, correctedLabel: string, rawLabel: string): void {
    log('vision_correct_label', { trackId, correctedLabel, rawLabel })
    this.ws.send('vision_correct_label', { track_id: trackId, corrected_label: correctedLabel, raw_label: rawLabel })
  }

  requestSnapshot(opts: { width?: number; height?: number; quality?: number } = {}): void {
    log('camera_snapshot')
    this.ws.send('camera_snapshot', {
      width: opts.width ?? 1280,
      height: opts.height ?? 720,
      quality: opts.quality ?? 75,
      request_id: nextRequestId(),
    })
  }

  requestPresets(): void {
    this.ws.send('camera_list_presets')
  }

  requestPosition(): void {
    this.ws.send('camera_get_position', { request_id: nextRequestId() })
  }

  requestStatus(): void {
    this.ws.send('camera_status', { request_id: nextRequestId() })
  }

  requestHealth(): void {
    this.ws.send('vision_health')
  }

  requestEvents(sinceSeq = 0): void {
    this.ws.send('vision_events', { since_seq: sinceSeq })
  }

  requestCommandLog(last = 50): void {
    this.ws.send('command_log', { last })
  }

  requestLabelCorrections(): void {
    this.ws.send('vision_get_label_corrections')
  }

  injectFault(fault: string, active: boolean): void {
    this.ws.send('fault_inject', { fault, active })
  }

  requestFaultStatus(): void {
    this.ws.send('fault_status')
  }

  // ── Authority ───────────────────────────────────────────────────

  claimAuthority(who: string, reason = ''): void {
    log('authority_claim', { who, reason })
    this.ws.send('authority_claim', { who, reason })
  }

  requestAuthorityState(): void {
    this.ws.send('authority_state')
  }

  // ── Pipeline metrics ────────────────────────────────────────────

  requestPipelineMetrics(): void {
    this.ws.send('pipeline_metrics')
  }

  // ── Camera registry ─────────────────────────────────────────────

  requestCameraRegistry(): void {
    this.ws.send('camera_registry')
  }

  // ── PTZ control ─────────────────────────────────────────────────

  ptzMove(direction: PtzDirection, speed = 1, durationMs = 150): void {
    log('ptz_move', { direction, speed, durationMs })
    this.ws.send('camera_ptz_move', {
      direction,
      speed,
      duration_ms: durationMs,
      request_id: nextRequestId(),
    })
  }

  ptzSetPosition(pan: number, tilt: number, zoom: number): void {
    log('ptz_set_position', { pan, tilt, zoom })
    this.ws.send('camera_ptz_set_position', {
      pan, tilt, zoom,
      request_id: nextRequestId(),
    })
  }

  ptzRelative(panDelta: number, tiltDelta: number, zoomDelta: number): void {
    log('ptz_relative', { panDelta, tiltDelta, zoomDelta })
    this.ws.send('camera_ptz_relative', {
      pan_delta: panDelta,
      tilt_delta: tiltDelta,
      zoom_delta: zoomDelta,
      request_id: nextRequestId(),
    })
  }

  ptzStop(): void {
    log('ptz_stop')
    this.ws.send('camera_ptz_stop', { request_id: nextRequestId() })
  }

  // ── Realtime PTZ motion protocol ──────────────────────────────

  ptzStartMotion(opts: {
    motionId: string
    panVelocity: number
    tiltVelocity: number
    zoomVelocity?: number
    speed?: number
    durationGuardMs?: number
  }): void {
    log('ptz_start_motion', opts)
    this.ws.send('camera_ptz_start_motion', {
      motion_id: opts.motionId,
      pan_velocity: opts.panVelocity,
      tilt_velocity: opts.tiltVelocity,
      zoom_velocity: opts.zoomVelocity ?? 0,
      speed: opts.speed ?? 1,
      duration_guard_ms: opts.durationGuardMs ?? 500,
      timestamp: Date.now(),
      request_id: nextRequestId(),
    })
  }

  ptzUpdateMotion(opts: {
    motionId: string
    panVelocity: number
    tiltVelocity: number
    zoomVelocity?: number
    speed?: number
  }): void {
    this.ws.send('camera_ptz_update_motion', {
      motion_id: opts.motionId,
      pan_velocity: opts.panVelocity,
      tilt_velocity: opts.tiltVelocity,
      zoom_velocity: opts.zoomVelocity ?? 0,
      speed: opts.speed ?? 1,
      timestamp: Date.now(),
    })
  }

  ptzStopMotion(motionId: string): void {
    log('ptz_stop_motion', { motionId })
    this.ws.send('camera_ptz_stop_motion', {
      motion_id: motionId,
      timestamp: Date.now(),
      request_id: nextRequestId(),
    })
  }

  zoomStartMotion(motionId: string, zoomVelocity: number, speed = 1): void {
    log('zoom_start_motion', { motionId, zoomVelocity })
    this.ws.send('camera_zoom_start', {
      motion_id: motionId,
      zoom_velocity: zoomVelocity,
      speed,
      duration_guard_ms: 500,
      timestamp: Date.now(),
      request_id: nextRequestId(),
    })
  }

  zoomUpdateMotion(motionId: string, zoomVelocity: number, speed = 1): void {
    this.ws.send('camera_zoom_update', {
      motion_id: motionId,
      zoom_velocity: zoomVelocity,
      speed,
      timestamp: Date.now(),
    })
  }

  zoomStopMotion(motionId: string): void {
    log('zoom_stop_motion', { motionId })
    this.ws.send('camera_zoom_stop', {
      motion_id: motionId,
      timestamp: Date.now(),
      request_id: nextRequestId(),
    })
  }

  ptzHome(): void {
    log('ptz_home')
    this.ptzSetPosition(0, 0, 100)
  }

  zoomIn(step = 10): void {
    this.ptzRelative(0, 0, step)
  }

  zoomOut(step = 10): void {
    this.ptzRelative(0, 0, -step)
  }

  // ── Quality mode ────────────────────────────────────────────────

  switchQuality(mode: { fps: number; width: number; height: number; quality: number }): void {
    log('switch_quality', mode)
    this.stopCamera()
    this.startCamera(mode)
    this.subscribe(mode.fps, mode.quality)
  }

  // ── Scene / Tracking / Watch / Follow ──────────────────────────

  requestSceneState(): void {
    this.ws.send('vision_scene_state')
  }

  analyzeFrame(transcript = ''): void {
    log('analyze_frame', { transcript })
    this.ws.send('vision_analyze', { transcript })
  }

  trackStart(label: string, hint = ''): void {
    log('track_start', { label, hint })
    this.ws.send('vision_track_start', { label, hint })
  }

  trackStop(label: string): void {
    log('track_stop', { label })
    this.ws.send('vision_track_stop', { label })
  }

  labelItem(label: string, frameId = ''): void {
    log('label_item', { label, frameId })
    this.ws.send('vision_label_item', { label, frame_id: frameId })
  }

  watchStart(target: string, condition = 'moved'): void {
    log('watch_start', { target, condition })
    this.ws.send('vision_watch_start', { target, condition })
  }

  watchStop(target: string): void {
    log('watch_stop', { target })
    this.ws.send('vision_watch_stop', { target })
  }

  followStart(target = 'operator'): void {
    log('follow_start', { target })
    this.ws.send('vision_follow_start', { target })
  }

  followStop(): void {
    log('follow_stop')
    this.ws.send('vision_follow_stop')
  }

  queryVisual(target: string): void {
    log('query_visual', { target })
    this.ws.send('vision_query', { target })
  }

  sceneDescribe(): void {
    log('scene_describe')
    this.ws.send('vision_scene_describe')
  }

  requestActiveTracks(): void {
    this.ws.send('vision_active_tracks')
  }

  trackQuery(label: string): void {
    log('track_query', { label })
    this.ws.send('vision_track_query', { label })
  }

  lookAt(label: string): void {
    log('look_at', { label })
    this.ws.send('vision_look_at', { label })
  }

  // ── Tracker stack ──────────────────────────────────────────────

  enableTracker(category: string): void {
    log('tracker_enable', { category })
    this.ws.send('vision_tracker_enable', { category })
  }

  disableTracker(category: string): void {
    log('tracker_disable', { category })
    this.ws.send('vision_tracker_disable', { category })
  }

  setTrackerStack(categories: string[]): void {
    log('tracker_stack', { categories })
    this.ws.send('vision_tracker_stack', { categories })
  }

  stopAllTracking(): void {
    log('stop_all_tracking')
    this.ws.send('vision_stop_all_tracking')
  }

  requestTrackerState(): void {
    this.ws.send('vision_tracker_state')
  }

  // ── Preset CRUD ────────────────────────────────────────────────

  createPreset(presetId: string, label: string, description = '', ptz?: { pan: number; tilt: number; zoom: number }): void {
    log('preset_create', { presetId, label })
    this.ws.send('vision_preset_create', { preset_id: presetId, label, description, ptz })
  }

  renamePreset(presetId: string, newLabel: string): void {
    log('preset_rename', { presetId, newLabel })
    this.ws.send('vision_preset_rename', { preset_id: presetId, new_label: newLabel })
  }

  deletePreset(presetId: string): void {
    log('preset_delete', { presetId })
    this.ws.send('vision_preset_delete', { preset_id: presetId })
  }

  activatePreset(presetId: string): void {
    log('preset_activate', { presetId })
    this.ws.send('vision_preset_activate', { preset_id: presetId })
  }

  updatePresetPtz(presetId: string, ptz: { pan: number; tilt: number; zoom: number }): void {
    log('preset_update_ptz', { presetId, ptz })
    this.ws.send('vision_preset_update_ptz', { preset_id: presetId, ptz })
  }

  nudgePreset(presetId: string, panDelta: number, tiltDelta: number, zoomDelta: number): void {
    log('preset_nudge', { presetId, panDelta, tiltDelta, zoomDelta })
    this.ws.send('vision_preset_nudge', { preset_id: presetId, pan_delta: panDelta, tilt_delta: tiltDelta, zoom_delta: zoomDelta })
  }

  requestPresetState(): void {
    this.ws.send('vision_preset_state')
  }

  // ── Trigger chains ─────────────────────────────────────────────

  createChain(opts: { label: string; trigger_event: string; actions: Array<{ type: string; [key: string]: unknown }>; conditions?: Array<{ field: string; op: string; value: unknown }>; trigger_zone?: string; confidence_min?: number; debounce_seconds?: number }): void {
    log('chain_create', opts)
    this.ws.send('vision_chain_create', opts)
  }

  deleteChain(chainId: string): void {
    log('chain_delete', { chainId })
    this.ws.send('vision_chain_delete', { chain_id: chainId })
  }

  enableChain(chainId: string): void {
    log('chain_enable', { chainId })
    this.ws.send('vision_chain_enable', { chain_id: chainId })
  }

  disableChain(chainId: string): void {
    log('chain_disable', { chainId })
    this.ws.send('vision_chain_disable', { chain_id: chainId })
  }

  explainChain(chainId = ''): void {
    log('chain_explain', { chainId })
    this.ws.send('vision_chain_explain', { chain_id: chainId })
  }

  requestChainState(): void {
    this.ws.send('vision_chain_state')
  }

  // ── Security mode ──────────────────────────────────────────────

  activateSecurityMode(triggeredBy = 'operator_command'): void {
    log('security_activate', { triggeredBy })
    this.ws.send('vision_security_activate', { triggered_by: triggeredBy })
  }

  deactivateSecurityMode(): void {
    log('security_deactivate')
    this.ws.send('vision_security_deactivate')
  }

  requestSecurityState(): void {
    this.ws.send('vision_security_state')
  }

  // ── Diagnostic overlay ─────────────────────────────────────────

  setDiagnosticOverlay(enabled: boolean): void {
    log('diagnostic_overlay', { enabled })
    this.ws.send('vision_diagnostic_overlay', { enabled })
  }

  // ── Events ──────────────────────────────────────────────────────

  on(type: string, handler: (data: Record<string, unknown>) => void): () => void {
    return this.ws.on(type, handler)
  }

  // ── Internal ────────────────────────────────────────────────────

  private _enqueueFrame(buf: ArrayBuffer): void {
    this._frameSizes.push(buf.byteLength)
    if (this._frameSizes.length > 30) this._frameSizes.shift()
    this._fpsWindow.push(Date.now())

    this._pendingFrame = buf
    if (this._rafId === null) {
      this._rafId = requestAnimationFrame(() => this._flushFrame())
    }
  }

  private _flushFrame(): void {
    this._rafId = null
    const buf = this._pendingFrame
    if (!buf) return
    this._pendingFrame = null

    const blob = new Blob([buf], { type: 'image/jpeg' })
    const newUrl = URL.createObjectURL(blob)

    const oldUrl = this._prevBlobUrl
    this._latestFrameUrl = newUrl
    this._prevBlobUrl = newUrl
    this._frameCount++

    if (this._frameCount === 1) log('first_frame_received', `bytes=${buf.byteLength}`)
    if (this._frameCount % 100 === 0) log('frames_received', this._frameCount)

    const handlers = (this.ws as unknown as { handlers: Map<string, ((d: Record<string, unknown>) => void)[]> }).handlers?.get('vision_frame') || []
    for (const h of handlers) {
      h({ type: 'vision_frame', url: newUrl, timestamp: Date.now(), byteLength: buf.byteLength })
    }

    if (oldUrl) {
      setTimeout(() => URL.revokeObjectURL(oldUrl), 100)
    }
  }

  private _revokeFrame(): void {
    if (this._rafId !== null) {
      cancelAnimationFrame(this._rafId)
      this._rafId = null
    }
    this._pendingFrame = null
    if (this._prevBlobUrl) {
      URL.revokeObjectURL(this._prevBlobUrl)
      this._prevBlobUrl = null
    }
  }
}
