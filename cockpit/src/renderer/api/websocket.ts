type WsHandler = (data: Record<string, unknown>) => void

export class WsClient {
  private ws: WebSocket | null = null
  private handlers = new Map<string, WsHandler[]>()
  private _binaryHandlers: ((data: ArrayBuffer) => void)[] = []
  private reconnectDelay = 1000
  private shouldReconnect = true

  constructor(private url: string, private protocols?: string[]) {}

  connect(): void {
    try {
      this.ws = this.protocols
        ? new WebSocket(this.url, this.protocols)
        : new WebSocket(this.url)

      this.ws.onopen = () => {
        this.reconnectDelay = 1000
        this.emit('connected', {})
      }

      this.ws.onmessage = (event: MessageEvent) => {
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
        this.emit('disconnected', {})
        if (this.shouldReconnect) {
          setTimeout(() => this.connect(), this.reconnectDelay)
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000)
        }
      }

      this.ws.onerror = () => {
        this.ws?.close()
      }
    } catch {
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
    this.ws?.close()
    this.ws = null
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  private emit(type: string, data: Record<string, unknown>): void {
    for (const handler of this.handlers.get(type) || []) {
      handler(data)
    }
  }
}
