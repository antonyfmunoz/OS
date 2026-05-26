import { WsClient } from './websocket'

const VOICE_URL = import.meta.env.VITE_VOICE_URL as string || 'ws://localhost:8095/voice'
const TARGET_SAMPLE_RATE = 16000
const CHUNK_SIZE = 4096

export type VoiceEvent =
  | { type: 'transcript'; text: string; final: boolean }
  | { type: 'vad_status'; active: boolean }
  | { type: 'tts_status'; speaking: boolean }
  | { type: 'audio_level'; level: number }
  | { type: 'voice_response'; text: string; spoken_text: string; classification: string; has_audio: boolean }
  | { type: 'connected' }
  | { type: 'disconnected' }

export class VoiceWsClient {
  private ws: WsClient
  private mediaStream: MediaStream | null = null
  private audioContext: AudioContext | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private processorNode: ScriptProcessorNode | null = null
  private _expectingAudio = false

  constructor() {
    this.ws = new WsClient(VOICE_URL)
    this.ws.onBinary((buf) => this._handleBinary(buf))
  }

  connect(): void {
    this.ws.connect()
  }

  disconnect(): void {
    this.stopMic()
    this.ws.disconnect()
  }

  async startMic(): Promise<void> {
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: TARGET_SAMPLE_RATE,
        },
      })

      this.audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE })
      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream)
      this.processorNode = this.audioContext.createScriptProcessor(CHUNK_SIZE, 1, 1)

      this.processorNode.onaudioprocess = (e: AudioProcessingEvent) => {
        const float32 = e.inputBuffer.getChannelData(0)
        const pcm16 = new Int16Array(float32.length)
        for (let i = 0; i < float32.length; i++) {
          const s = Math.max(-1, Math.min(1, float32[i]))
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
        }
        this.ws.sendBinary(pcm16.buffer)
      }

      this.sourceNode.connect(this.processorNode)
      this.processorNode.connect(this.audioContext.destination)

      this.ws.send('mic_start')
    } catch (err) {
      console.error('[VoiceWS] Mic access failed:', err)
    }
  }

  stopMic(): void {
    this.ws.send('mic_stop')

    this.processorNode?.disconnect()
    this.sourceNode?.disconnect()
    this.processorNode = null
    this.sourceNode = null

    if (this.audioContext?.state !== 'closed') {
      this.audioContext?.close()
    }
    this.audioContext = null

    this.mediaStream?.getTracks().forEach(t => t.stop())
    this.mediaStream = null
  }

  on(type: string, handler: (data: Record<string, unknown>) => void): () => void {
    if (type === 'voice_response') {
      return this.ws.on(type, (data) => {
        if (data.has_audio) this._expectingAudio = true
        handler(data)
      })
    }
    return this.ws.on(type, handler)
  }

  get connected(): boolean {
    return this.ws.connected
  }

  private _handleBinary(buf: ArrayBuffer): void {
    if (!this._expectingAudio) return
    this._expectingAudio = false
    this._playWav(buf)
  }

  private _playWav(buf: ArrayBuffer): void {
    try {
      const blob = new Blob([buf], { type: 'audio/wav' })
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.onended = () => URL.revokeObjectURL(url)
      audio.onerror = () => URL.revokeObjectURL(url)
      audio.play().catch(err => console.error('[VoiceWS] Playback failed:', err))
    } catch (err) {
      console.error('[VoiceWS] WAV play error:', err)
    }
  }
}
