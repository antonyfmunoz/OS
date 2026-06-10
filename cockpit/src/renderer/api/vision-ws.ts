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

  constructor() {
    this.ws = new WsClient(VISION_URL, getVisionProtocols())
    this.ws.onBinary((buf) => this._handleFrame(buf))
  }

  connect(): Promise<void> {
    log('ws_connect', VISION_URL)
    return new Promise<void>((resolve, reject) => {
      const onConnected = this.ws.on('connected', () => {
        log('ws_connected')
        onConnected()
        clearTimeout(timer)
        resolve()
      })
      const onDisconnected = this.ws.on('disconnected', () => {
        log('ws_connect_failed', 'disconnected during connect')
        onDisconnected()
        clearTimeout(timer)
        reject(new Error('Vision relay disconnected during connect'))
      })
      const timer = setTimeout(() => {
        onConnected()
        onDisconnected()
        log('ws_connect_timeout', '5s elapsed')
        reject(new Error('Vision relay connection timed out'))
      }, 5000)
      this.ws.connect()
    })
  }

  disconnect(): void {
    log('disconnect')
    this._revokeFrame()
    this.ws.disconnect()
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

  setPreset(preset: string): void {
    log('camera_preset', preset)
    this.ws.send('camera_preset', { preset, request_id: nextRequestId() })
  }

  savePreset(preset: string, label: string, analysisHint = ''): void {
    log('camera_save_preset', { preset, label })
    this.ws.send('camera_save_preset', { preset, label, analysis_hint: analysisHint, request_id: nextRequestId() })
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
    this.ws.send('camera_status')
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

  // ── Events ──────────────────────────────────────────────────────

  on(type: string, handler: (data: Record<string, unknown>) => void): () => void {
    return this.ws.on(type, handler)
  }

  // ── Internal ────────────────────────────────────────────────────

  private _handleFrame(buf: ArrayBuffer): void {
    this._revokeFrame()
    const blob = new Blob([buf], { type: 'image/jpeg' })
    this._latestFrameUrl = URL.createObjectURL(blob)
    this._prevBlobUrl = this._latestFrameUrl
    this._frameCount++

    this._fpsWindow.push(Date.now())
    this._frameSizes.push(buf.byteLength)
    if (this._frameSizes.length > 30) this._frameSizes.shift()

    if (this._frameCount === 1) log('first_frame_received', `bytes=${buf.byteLength}`)
    if (this._frameCount % 100 === 0) log('frames_received', this._frameCount)

    const handlers = (this.ws as unknown as { handlers: Map<string, ((d: Record<string, unknown>) => void)[]> }).handlers?.get('vision_frame') || []
    for (const h of handlers) {
      h({ type: 'vision_frame', url: this._latestFrameUrl, timestamp: Date.now(), byteLength: buf.byteLength })
    }
  }

  private _revokeFrame(): void {
    if (this._prevBlobUrl) {
      URL.revokeObjectURL(this._prevBlobUrl)
      this._prevBlobUrl = null
    }
  }
}
