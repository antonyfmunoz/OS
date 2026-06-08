import { WsClient } from './websocket'

const VOICE_URL = import.meta.env.VITE_VOICE_URL as string || 'ws://localhost:8096/voice'
const TARGET_SAMPLE_RATE = 16000
const CHUNK_SIZE = 4096

export type VoiceEvent =
  | { type: 'transcript'; text: string; final: boolean }
  | { type: 'vad_status'; active: boolean }
  | { type: 'tts_status'; speaking: boolean }
  | { type: 'tts_error'; error: string }
  | { type: 'audio_level'; level: number }
  | { type: 'connected' }
  | { type: 'disconnected' }

export class VoiceWsClient {
  private ws: WsClient
  private mediaStream: MediaStream | null = null
  private audioContext: AudioContext | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private processorNode: ScriptProcessorNode | null = null
  private _audioQueue: ArrayBuffer[] = []
  private _playing = false
  private _currentAudio: HTMLAudioElement | null = null

  constructor() {
    this.ws = new WsClient(VOICE_URL)
    this.ws.onBinary((buf) => this._queueAudio(buf))
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
    return this.ws.on(type, handler)
  }

  get connected(): boolean {
    return this.ws.connected
  }

  requestTts(text: string): void {
    this.ws.send('tts_request', { text })
  }

  cancelTts(): void {
    this._audioQueue = []
    if (this._currentAudio) {
      this._currentAudio.pause()
      this._currentAudio = null
    }
    this._playing = false
    this.ws.send('tts_cancel')
  }

  private _queueAudio(buf: ArrayBuffer): void {
    this._audioQueue.push(buf)
    if (!this._playing) this._playNext()
  }

  private _playNext(): void {
    const buf = this._audioQueue.shift()
    if (!buf) {
      this._playing = false
      this._currentAudio = null
      return
    }
    this._playing = true
    try {
      const blob = new Blob([buf], { type: 'audio/wav' })
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      this._currentAudio = audio
      audio.onended = () => { URL.revokeObjectURL(url); this._playNext() }
      audio.onerror = () => { URL.revokeObjectURL(url); this._playNext() }
      audio.play().catch(() => this._playNext())
    } catch {
      this._playNext()
    }
  }
}
