import { WsClient } from './websocket'

function getBrowserUrl(paneId: string): string {
  if (import.meta.env.VITE_BROWSER_URL) {
    const base = import.meta.env.VITE_BROWSER_URL as string
    return `${base}${base.includes('?') ? '&' : '?'}pane=${paneId}`
  }

  const isLocalhost =
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
  const isElectron = Boolean((window as Record<string, unknown>).cockpit)

  if (isElectron || isLocalhost) {
    return `ws://localhost:8086/browser?pane=${paneId}`
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/umh/browser/ws?pane=${paneId}`
}

function getBrowserProtocols(): string[] {
  const token = import.meta.env.VITE_BROWSER_RELAY_TOKEN as string | undefined
  if (token) return [`auth.${token}`]
  return []
}

export interface BrowserFrameEvent {
  url: string
  timestamp: number
  byteLength: number
}

export type BrowserEventHandler = (data: Record<string, unknown>) => void

export class BrowserWsClient {
  private ws: WsClient
  private _paneId: string
  private _prevBlobUrl: string | null = null
  private _latestFrameUrl: string | null = null
  private _frameCount = 0
  private _fpsWindow: number[] = []
  private _pendingFrame: ArrayBuffer | null = null
  private _rafId: number | null = null
  private _frameHandlers: ((event: BrowserFrameEvent) => void)[] = []

  constructor(paneId: string) {
    this._paneId = paneId
    const url = getBrowserUrl(paneId)
    this.ws = new WsClient(url, getBrowserProtocols())
    this.ws.onBinary((buf) => this._enqueueFrame(buf))
  }

  connect(): void {
    this.ws.connect()
  }

  disconnect(): void {
    this._revokeFrame()
    this.ws.disconnect()
  }

  reconnect(): void {
    this.ws.disconnect()
    setTimeout(() => {
      const url = getBrowserUrl(this._paneId)
      this.ws = new WsClient(url, getBrowserProtocols())
      this.ws.onBinary((buf) => this._enqueueFrame(buf))
      this.ws.connect()
    }, 500)
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

  // ── Input ──────────────────────────────────────────────────

  sendMouse(
    action: string,
    x: number,
    y: number,
    opts?: { button?: string; clickCount?: number; deltaX?: number; deltaY?: number }
  ): void {
    this.ws.send('mouse', { action, x, y, ...opts })
  }

  sendKey(
    action: string,
    key: string,
    code: string,
    opts?: { text?: string; modifiers?: number }
  ): void {
    this.ws.send('key', { action, key, code, ...opts })
  }

  insertText(text: string): void {
    this.ws.send('insertText', { text })
  }

  navigate(url: string): void {
    this.ws.send('navigate', { url })
  }

  goBack(): void {
    this.ws.send('back')
  }

  goForward(): void {
    this.ws.send('forward')
  }

  reload(): void {
    this.ws.send('reload')
  }

  resize(width: number, height: number): void {
    this.ws.send('resize', { width, height })
  }

  // ── Events ──────────────────────────────────────────────────

  onFrame(handler: (event: BrowserFrameEvent) => void): () => void {
    this._frameHandlers.push(handler)
    return () => {
      this._frameHandlers = this._frameHandlers.filter((h) => h !== handler)
    }
  }

  on(type: string, handler: BrowserEventHandler): () => void {
    return this.ws.on(type, handler)
  }

  // ── Frame pipeline ─────────────────────────────────────────

  private _enqueueFrame(buf: ArrayBuffer): void {
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

    const preload = new Image()
    preload.onload = () => {
      const oldUrl = this._prevBlobUrl
      this._latestFrameUrl = newUrl
      this._prevBlobUrl = newUrl
      this._frameCount++

      const event: BrowserFrameEvent = {
        url: newUrl,
        timestamp: Date.now(),
        byteLength: buf.byteLength,
      }
      for (const h of this._frameHandlers) h(event)

      if (oldUrl) {
        setTimeout(() => URL.revokeObjectURL(oldUrl), 200)
      }
    }
    preload.onerror = () => {
      URL.revokeObjectURL(newUrl)
    }
    preload.src = newUrl
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
