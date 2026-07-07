import { WsClient } from './websocket'
import {
  playTtsAudio,
  cancelPlayback,
  setPlaybackCallbacks,
} from './tts-playback-controller'

function getVoiceUrl(): string {
  if (import.meta.env.VITE_VOICE_URL) return import.meta.env.VITE_VOICE_URL as string

  const isLocalhost =
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
  const isElectron = Boolean((window as Record<string, unknown>).cockpit)

  if (isElectron || isLocalhost) {
    return 'ws://localhost:8096/voice'
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/umh/voice/ws`
}
const VOICE_URL = getVoiceUrl()
const TARGET_SAMPLE_RATE = 16000
const CHUNK_SIZE = 4096

const log = (stage: string, ...args: unknown[]) =>
  console.log(`[VoicePipeline] ${stage}`, ...args)

log('voice_ws_url_resolved', VOICE_URL)

export type VoiceEvent =
  | { type: 'transcript'; text: string; final: boolean }
  | { type: 'vad_status'; active: boolean }
  | { type: 'tts_status'; speaking: boolean }
  | { type: 'tts_error'; error: string }
  | { type: 'audio_level'; level: number }
  | { type: 'connected' }
  | { type: 'disconnected' }
  | { type: 'error'; code: string; message: string }

export class VoiceWsClient {
  private ws: WsClient
  private mediaStream: MediaStream | null = null
  private audioContext: AudioContext | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private processorNode: ScriptProcessorNode | null = null
  private _sinkNode: GainNode | null = null
  private _audioQueue: ArrayBuffer[] = []
  private _playing = false
  private _currentAudio: HTMLAudioElement | null = null
  private _chunkCount = 0
  /** P4S-31D1-C: rolling client-side RMS of the mic stream (0..1). If this
   * stays 0 while the user speaks, the mic stream is silent — the exact
   * failure the audio-signal contract catches. Sourced from the SAME PCM the
   * server sees, so client and server RMS should agree. Read by the ~10Hz
   * meter poll in voice-controller (client.clientRms). Moves even if the
   * server emits no audio_level events. */
  private _lastClientRms = 0
  private _maxClientRms = 0
  /** Wall-clock ms of the last buffer processed (capture liveness). */
  private _lastCaptureTs = 0

  constructor() {
    this.ws = new WsClient(VOICE_URL)
    this.ws.onBinary((buf) => this._queueAudio(buf))
  }

  connect(): Promise<void> {
    log('ws_connect', VOICE_URL)
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
        reject(new Error('Voice server disconnected during connect'))
      })
      const timer = setTimeout(() => {
        onConnected()
        onDisconnected()
        log('ws_connect_timeout', '5s elapsed')
        reject(new Error('Voice server connection timed out'))
      }, 5000)
      this.ws.connect()
    })
  }

  disconnect(): void {
    log('disconnect')
    this.stopMic()
    this.ws.disconnect()
  }

  async startMic(): Promise<{
    stream: MediaStream
    trackState: string
    diagnostics: Record<string, unknown>
  }> {
    log('mic_permission_request')

    if (!navigator.mediaDevices?.getUserMedia) {
      throw Object.assign(new Error('Browser does not support microphone capture'), { name: 'NotSupportedError' })
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: TARGET_SAMPLE_RATE,
      },
    })

    const tracks = stream.getAudioTracks()
    log('mic_stream_acquired', `tracks=${tracks.length}`)

    if (tracks.length === 0) {
      stream.getTracks().forEach(t => t.stop())
      throw Object.assign(new Error('No audio track in stream'), { name: 'NotFoundError' })
    }

    const track = tracks[0]
    log('mic_track_state', track.readyState, track.label)

    if (track.readyState !== 'live') {
      stream.getTracks().forEach(t => t.stop())
      throw Object.assign(new Error(`Audio track not live: ${track.readyState}`), { name: 'NotFoundError' })
    }

    this.mediaStream = stream
    this._chunkCount = 0
    this._lastClientRms = 0
    this._maxClientRms = 0
    this.audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE })

    // P4S-31D1-C ROOT-CAUSE FIX: a browser AudioContext is created 'suspended'
    // until resumed after a user gesture. Without this resume the
    // ScriptProcessor's onaudioprocess NEVER fires — zero PCM chunks reach the
    // server, RMS is 0, and every recording ends in "No speech detected". The
    // TTS playback context already resumes (unlockAudioForIOS); the capture
    // context did not. Resume it explicitly.
    if (this.audioContext.state === 'suspended') {
      try {
        await this.audioContext.resume()
        log('capture_audio_context_resumed')
      } catch (e) {
        log('capture_audio_context_resume_failed', e)
      }
    }
    log('capture_audio_context_state', this.audioContext.state)

    this.sourceNode = this.audioContext.createMediaStreamSource(stream)
    this.processorNode = this.audioContext.createScriptProcessor(CHUNK_SIZE, 1, 1)
    this._chunkCount = 0
    this._lastClientRms = 0
    this._maxClientRms = 0
    this._lastCaptureTs = 0

    this.processorNode.onaudioprocess = (e: AudioProcessingEvent) => {
      const float32 = e.inputBuffer.getChannelData(0)
      const pcm16 = new Int16Array(float32.length)
      let sumSq = 0
      for (let i = 0; i < float32.length; i++) {
        const s = Math.max(-1, Math.min(1, float32[i]))
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
        sumSq += s * s
      }
      // Client RMS on the SAME PCM the server measures (0..1, full-scale=1).
      // The single cheapest proof the mic is actually delivering samples — no
      // FFT, no per-frame allocation. Moves even if the server emits no
      // audio_level events; a live capture flat at 0 means a silent mic.
      const rms = float32.length ? Math.sqrt(sumSq / float32.length) : 0
      this._lastClientRms = rms
      if (rms > this._maxClientRms) this._maxClientRms = rms
      this._lastCaptureTs = Date.now()
      this.ws.sendBinary(pcm16.buffer)
      this._chunkCount++
      if (this._chunkCount === 1) log('first_audio_chunk_sent')
      if (this._chunkCount % 100 === 0) log('audio_chunks_sent', this._chunkCount)
    }

    // ScriptProcessor must connect to a destination to fire onaudioprocess, but
    // routing the mic to the speakers would echo. Sink through a zero-gain node.
    this._sinkNode = this.audioContext.createGain()
    this._sinkNode.gain.value = 0
    this.sourceNode.connect(this.processorNode)
    this.processorNode.connect(this._sinkNode)
    this._sinkNode.connect(this.audioContext.destination)

    this.ws.send('mic_start')
    log('mic_start_sent')

    return {
      stream,
      trackState: track.readyState,
      diagnostics: this.captureDiagnostics(),
    }
  }

  /**
   * P4S-31D1-C: non-secret capture diagnostics for one recording. No audio
   * bytes, no transcript — settings + counters only.
   */
  captureDiagnostics(): Record<string, unknown> {
    const track = this.mediaStream?.getAudioTracks()[0]
    const settings = track?.getSettings?.() ?? {}
    return {
      audio_context_state: this.audioContext?.state ?? 'none',
      audio_context_sample_rate: this.audioContext?.sampleRate ?? null,
      chunk_count: this._chunkCount,
      last_client_rms: Number(this._lastClientRms.toFixed(4)),
      max_client_rms: Number(this._maxClientRms.toFixed(4)),
      track_ready_state: track?.readyState ?? 'none',
      track_muted: track?.muted ?? null,
      track_enabled: track?.enabled ?? null,
      track_sample_rate: (settings as MediaTrackSettings).sampleRate ?? null,
      track_channel_count: (settings as MediaTrackSettings).channelCount ?? null,
      echo_cancellation: (settings as MediaTrackSettings).echoCancellation ?? null,
      noise_suppression: (settings as MediaTrackSettings).noiseSuppression ?? null,
      // Capture-liveness aliases (UI meter / P4S-31D1-C-UI contract): same
      // values, camelCase names the meter + ui-signal tests consume.
      clientRms: Number(this._lastClientRms.toFixed(4)),
      peakRms: Number(this._maxClientRms.toFixed(4)),
      chunksSent: this._chunkCount,
      lastCaptureMsAgo: this._lastCaptureTs ? Date.now() - this._lastCaptureTs : null,
      capturing: this.processorNode !== null && this.audioContext !== null,
    }
  }

  /** Live client RMS (0..1) for the recording meter. */
  get clientRms(): number {
    return this._lastClientRms
  }

  get maxClientRms(): number {
    return this._maxClientRms
  }

  stopMic(): void {
    log('mic_stop', `chunks_sent=${this._chunkCount}`)
    this.ws.send('mic_stop')

    this.processorNode?.disconnect()
    this.sourceNode?.disconnect()
    this._sinkNode?.disconnect()
    this.processorNode = null
    this.sourceNode = null
    this._sinkNode = null

    if (this.audioContext?.state !== 'closed') {
      this.audioContext?.close()
    }
    this.audioContext = null

    this.mediaStream?.getTracks().forEach(t => t.stop())
    this.mediaStream = null
    this._lastClientRms = 0
    this._maxClientRms = 0
    this._lastCaptureTs = 0
  }

  /** PCM16 buffers pushed to the server this session (capture liveness). */
  get chunksSent(): number {
    return this._chunkCount
  }

  /** Peak client RMS observed during the current capture (silence proof). */
  get peakRms(): number {
    return this._maxClientRms
  }

  /**
   * Send a bare control frame (e.g. 'mic_start' / 'mic_stop') without touching
   * getUserMedia. Used by the Lane E retry path, which streams a stored blob's
   * PCM rather than live mic audio.
   */
  sendControl(type: string): void {
    this.ws.send(type)
  }

  /** Stream one PCM16 chunk over the WS (retry path — no live mic). */
  sendPcm(buf: ArrayBuffer): void {
    this.ws.sendBinary(buf)
  }

  on(type: string, handler: (data: Record<string, unknown>) => void): () => void {
    return this.ws.on(type, handler)
  }

  get connected(): boolean {
    return this.ws.connected
  }

  requestTts(text: string): void {
    log('tts_request', text.slice(0, 60))
    this.ws.send('tts_request', { text })
  }

  cancelTts(): void {
    this._audioQueue = []
    if (this._currentAudio) {
      this._currentAudio.pause()
      this._currentAudio = null
    }
    this._playing = false
    cancelPlayback()
    this.ws.send('tts_cancel')
    log('tts_cancelled')
  }

  private _queueAudio(buf: ArrayBuffer): void {
    log('[TTSPlayback] audio_chunk_received', `bytes=${buf.byteLength}`)
    this._audioQueue.push(buf)
    if (!this._playing) this._playNext()
  }

  private _playNext(): void {
    const buf = this._audioQueue.shift()
    if (!buf) {
      this._playing = false
      this._currentAudio = null
      log('[TTSPlayback] queue_empty')
      return
    }
    this._playing = true
    log('[TTSPlayback] playing_chunk', `bytes=${buf.byteLength}`)
    playTtsAudio(buf)
    // The tts-playback-controller handles sequential playback internally.
    // We mark ourselves as done after queueing since the controller owns
    // the actual Audio element lifecycle.
    this._playing = false
    this._playNext()
  }
}
