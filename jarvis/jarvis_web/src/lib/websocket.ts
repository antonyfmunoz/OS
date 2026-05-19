type EventHandler = (type: string, data: unknown) => void

export class CockpitSocket {
  private ws: WebSocket | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private handler: EventHandler
  private onStatus: (connected: boolean) => void

  constructor(handler: EventHandler, onStatus: (connected: boolean) => void) {
    this.handler = handler
    this.onStatus = onStatus
  }

  connect(url?: string): void {
    const target = url ?? `ws://${window.location.hostname}:8093/ws`
    this.ws = new WebSocket(target)

    this.ws.onopen = () => this.onStatus(true)

    this.ws.onclose = () => {
      this.onStatus(false)
      this.reconnectTimer = setTimeout(() => this.connect(url), 3000)
    }

    this.ws.onerror = () => this.ws?.close()

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as { type?: string; data?: unknown }
        if (msg.type && msg.type !== 'pong') {
          this.handler(msg.type, msg.data)
        }
      } catch {
        // ignore parse errors
      }
    }
  }

  disconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }

  send(type: string, data?: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }))
    }
  }
}
