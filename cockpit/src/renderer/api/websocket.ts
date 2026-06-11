type WsHandler = (data: Record<string, unknown>) => void

export class WsClient {
  private ws: WebSocket | null = null
  private handlers = new Map<string, WsHandler[]>()
  private _binaryHandlers: ((data: ArrayBuffer) => void)[] = []
  private reconnectDelay = 1000
  private shouldReconnect = true
  private _connecting = false
  private _heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private _lastMessageAt = 0
  private _visibilityHandler: (() => void) | null = null

  constructor(private url: string, private protocols?: string[]) {}

  connect(): void {
    if (this._connecting || this.ws?.readyState === WebSocket.OPEN) return
    this._connecting = true

    try {
      this.ws = this.protocols
        ? new WebSocket(this.url, this.protocols)
        : new WebSocket(this.url)
      this.ws.binaryType = 'arraybuffer'

      this.ws.onopen = () => {
        this._connecting = false
        this.reconnectDelay = 1000
        this._lastMessageAt = Date.now()
        this._startHeartbeat()
        this._bindVisibility()
        this.emit('connected', {})
      }

      this.ws.onmessage = (event: MessageEvent) => {
        this._lastMessageAt = Date.now()

        if (event.data instanceof ArrayBuffer) {
          for (const handler of this._binaryHandlers) handler(event.data)
          return
        }
        if (event.data instanceof Blob) {
          event.data.arrayBuffer().then(buf => {
            for (const handler of this._binaryHandlers) handler(buf)
          })
          return
        }
        try {
          const data = JSON.parse(event.data as string) as Record<string, unknown>
          const type = (data.type as string) || 'message'
          this.emit(type, data)
        } catch {
          // skip unparseable
        }
      }

      this.ws.onclose = () => {
        this._connecting = false
        this._stopHeartbeat()
        this.emit('disconnected', {})
        if (this.shouldReconnect) {
          setTimeout(() => this.connect(), this.reconnectDelay)
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000)
        }
      }

      this.ws.onerror = () => {
        this._connecting = false
        this.ws?.close()
      }
    } catch {
      this._connecting = false
      if (this.shouldReconnect) {
        setTimeout(() => this.connect(), this.reconnectDelay)
      }
    }
  }

  send(type: string, payload: Record<string, unknown> = {}): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...payload }))
    }
  }

  sendBinary(data: ArrayBuffer | Blob): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data)
    }
  }

  onBinary(handler: (data: ArrayBuffer) => void): () => void {
    this._binaryHandlers.push(handler)
    return () => {
      this._binaryHandlers = this._binaryHandlers.filter(h => h !== handler)
    }
  }

  on(type: string, handler: WsHandler): () => void {
    const existing = this.handlers.get(type) || []
    existing.push(handler)
    this.handlers.set(type, existing)
    return () => this.off(type, handler)
  }

  off(type: string, handler: WsHandler): void {
    const existing = this.handlers.get(type) || []
    this.handlers.set(type, existing.filter(h => h !== handler))
  }

  disconnect(): void {
    this.shouldReconnect = false
    this._stopHeartbeat()
    this._unbindVisibility()
    this.ws?.close()
    this.ws = null
    this._connecting = false
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  get lastMessageAge(): number {
    return this._lastMessageAt ? Date.now() - this._lastMessageAt : -1
  }

  private emit(type: string, data: Record<string, unknown>): void {
    for (const handler of this.handlers.get(type) || []) {
      handler(data)
    }
  }

  private _startHeartbeat(): void {
    this._stopHeartbeat()
    this._heartbeatTimer = setInterval(() => {
      if (!this.connected) return
      const staleMs = Date.now() - this._lastMessageAt
      if (staleMs > 45000) {
        this.ws?.close()
        return
      }
      this.send('ping')
    }, 15000)
  }

  private _stopHeartbeat(): void {
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer)
      this._heartbeatTimer = null
    }
  }

  private _bindVisibility(): void {
    if (this._visibilityHandler) return
    this._visibilityHandler = () => {
      if (document.visibilityState === 'visible' && !this.connected && this.shouldReconnect) {
        this.reconnectDelay = 1000
        this.connect()
      }
    }
    document.addEventListener('visibilitychange', this._visibilityHandler)
  }

  private _unbindVisibility(): void {
    if (this._visibilityHandler) {
      document.removeEventListener('visibilitychange', this._visibilityHandler)
      this._visibilityHandler = null
    }
  }
}
