import { WsClient } from './websocket'

const VOICE_URL = import.meta.env.VITE_VOICE_URL as string || 'ws://localhost:8095/voice'

export type VoiceEvent =
  | { type: 'transcript'; text: string; final: boolean }
  | { type: 'vad_status'; active: boolean }
  | { type: 'tts_status'; speaking: boolean }
  | { type: 'audio_level'; level: number }
  | { type: 'connected' }
  | { type: 'disconnected' }

export class VoiceWsClient {
  private ws: WsClient

  constructor() {
    this.ws = new WsClient(VOICE_URL)
  }

  connect(): void {
    this.ws.connect()
  }

  disconnect(): void {
    this.ws.disconnect()
  }

  startMic(): void {
    this.ws.send('mic_start')
  }

  stopMic(): void {
    this.ws.send('mic_stop')
  }

  speak(text: string): void {
    this.ws.send('tts_speak', { text })
  }

  on(type: string, handler: (data: Record<string, unknown>) => void): () => void {
    return this.ws.on(type, handler)
  }

  get connected(): boolean {
    return this.ws.connected
  }
}
