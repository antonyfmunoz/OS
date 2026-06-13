import { WsClient } from './websocket'

function getBroadcastUrl(): string {
  if (import.meta.env.VITE_BROADCAST_URL) return import.meta.env.VITE_BROADCAST_URL as string

  const isLocalhost =
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
  const isElectron = Boolean((window as Record<string, unknown>).cockpit)

  if (isElectron || isLocalhost) {
    return 'ws://localhost:8095/api/umh/broadcast/ws'
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/umh/broadcast/ws`
}

const BROADCAST_URL = getBroadcastUrl()

export interface BroadcastHealthMetrics {
  frame: number
  fps: number
  bitrate_kbps: number
  drop_frames: number
  out_time_ms: number
  speed: string
  total_size_bytes: number
  uptime_s: number
  drop_percentage: number
  status_tier: 'HEALTHY' | 'WARNING' | 'CRITICAL'
}

export interface BroadcastPulse {
  type: 'broadcast_pulse'
  state: string
  health: BroadcastHealthMetrics | null
  latest_health: BroadcastHealthMetrics | null
  config: Record<string, unknown> | null
  pid: number | null
}

type BroadcastEventHandler = (data: BroadcastPulse) => void

export class BroadcastWsClient {
  private ws: WsClient
  private handlers: Set<BroadcastEventHandler> = new Set()

  constructor() {
    this.ws = new WsClient(BROADCAST_URL)
    this.ws.on('broadcast_pulse', (data: BroadcastPulse) => {
      for (const handler of this.handlers) {
        try {
          handler(data)
        } catch {
          // handler error
        }
      }
    })
  }

  connect(): void {
    this.ws.connect()
  }

  disconnect(): void {
    this.ws.disconnect()
    this.handlers.clear()
  }

  reconnect(): void {
    this.ws.disconnect()
    setTimeout(() => {
      this.ws = new WsClient(BROADCAST_URL)
      this.ws.on('broadcast_pulse', (data: BroadcastPulse) => {
        for (const handler of this.handlers) {
          try {
            handler(data)
          } catch {
            // handler error
          }
        }
      })
      this.ws.connect()
    }, 500)
  }

  get connected(): boolean {
    return this.ws.connected
  }

  on(handler: BroadcastEventHandler): () => void {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }
}
