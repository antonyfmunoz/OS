import { WsClient } from './websocket'
import {
  playTtsAudio,
  cancelPlayback,
  setPlaybackCallbacks,
} from './tts-playback-controller'

function getVoiceUrl(): string {
  if (import.meta.env.VITE_VOICE_URL) return import.meta.env.VITE_VOICE_URL as string

  // P4S31 Voice Convergence: every surface resolves to the ONE governed voice WS
  // on the API backend (proxied by nginx). The standalone voice server is retired;
  // localhost/Electron reach the same governed endpoint on the current host.
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/umh/voice/ws`
}
const VOICE_URL = getVoiceUrl()
const TARGET_SAMPLE_RATE = 16000

// Raw PCM16 mono@16kHz is the live-mic content type (no container decode server
// side — the runtime takes the preflight_pcm16 lane). The client resamples the
// captured blob to this before streaming.
const RAW_PCM_CONTENT_TYPE = 'audio/pcm'

const log = (stage: string, ...args: unknown[]) =>
  console.log(`[VoicePipeline] ${stage}`, ...args)

log('voice_ws_url_resolved', VOICE_URL)

/**
 * Prompt (or confirm) the browser/OS microphone permission on the user gesture,
 * then immediately release the probe stream. This is the FIRST consent layer —
 * the browser permission — surfaced up front so the single mic-tap handler can,
 * on its success, request the UMH push_to_talk grant WITHOUT a second user tap
 * (P4S-31D1-E single-gesture consent). Once the origin holds the permission the
 * subsequent full startMic() getUserMedia resolves silently (no re-prompt).
 *
 * Rejects with the original getUserMedia error (name preserved:
 * NotAllowedError / NotFoundError / NotSupportedError) so callers can branch on
 * a denied browser permission vs a failed server grant.
 *
 * P4S31 mobile fix: getUserMedia can HANG indefinitely on iOS Safari when the
 * mic was just granted/opened by a prior gesture and the OS audio session is
 * still held — it never resolves and never rejects, pinning the mic button at
 * "Requesting mic…" forever (this call runs before startCapture's 8s consent
 * watchdog, so that watchdog can't save it). Race it against a timeout and reject
 * with a MicAcquireTimeout (mapped by the caller to a typed, fast failure) so the
 * button degrades instead of dead-hanging.
 */
const MIC_ACQUIRE_TIMEOUT_MS = 10000

export async function ensureBrowserMicPermission(): Promise<void> {
  log('browser_mic_permission_probe')
  if (!navigator.mediaDevices?.getUserMedia) {
    throw Object.assign(
      new Error('Browser does not support microphone capture'),
      { name: 'NotSupportedError' },
    )
  }
  // P4S31 mobile fix: if the origin ALREADY holds mic permission, skip the probe
  // getUserMedia entirely — re-acquiring the mic while iOS still holds the audio
  // session from the initial grant is exactly what stalls. The real capture
  // stream (startMic) will open it once, cleanly. Only probe when the state is
  // 'prompt'/unknown (Permissions API is best-effort; absent on some browsers).
  try {
    const perm = await navigator.permissions?.query({
      name: 'microphone' as PermissionName,
    })
    if (perm?.state === 'granted') {
      log('browser_mic_permission_already_granted')
      return
    }
  } catch {
    // Permissions API unavailable (older Safari) — fall through to the probe.
  }
  let timer: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(Object.assign(
        new Error('Microphone did not open — release the mic and try again'),
        { name: 'MicAcquireTimeout' },
      ))
    }, MIC_ACQUIRE_TIMEOUT_MS)
  })
  let probe: MediaStream
  try {
    probe = await Promise.race([
      navigator.mediaDevices.getUserMedia({ audio: true }),
      timeout,
    ])
  } finally {
    if (timer) clearTimeout(timer)
  }
  // Permission is now granted for the origin; drop the probe tracks so the real
  // capture stream (startMic) is the only live one — no double-open, no prompt.
  probe.getTracks().forEach((t) => t.stop())
  log('browser_mic_permission_granted')
}

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
    this._lastCaptureTs = 0

    // P4S-31D1-F BLOB-ONLY: the voice-NOTE rail no longer streams live PCM to
    // the server during recording. `startMic` now ONLY acquires and validates
    // the raw mic MediaStream; the controller drives a MediaRecorder (the
    // playable blob → the sole transcription artifact) and a metering
    // AnalyserNode off this same stream. The deprecated ScriptProcessorNode
    // (broken on iOS Safari) and the old live-streaming path are gone — one
    // capture mechanism, one codec surface, nothing to diverge. On finalize,
    // `_transcribeBlob` resamples the blob and streams it once via the governed
    // GAP F protocol in `transcribeUtterance`.
    return {
      stream,
      trackState: track.readyState,
      diagnostics: this.captureDiagnostics(),
    }
  }

  /**
   * P4S-31D1-F: the metering AnalyserNode (in voice-controller) pushes the live
   * mic RMS here each tick so `clientRms` / `captureDiagnostics` stay the single
   * source of the "is the mic actually hearing me" signal — now sourced from the
   * AnalyserNode instead of the removed ScriptProcessor. Same 0..1 scale.
   */
  setMeterRms(rms: number): void {
    this._lastClientRms = rms
    if (rms > this._maxClientRms) this._maxClientRms = rms
    this._lastCaptureTs = Date.now()
    this._chunkCount++
  }

  /**
   * P4S-31D1-C: non-secret capture diagnostics for one recording. No audio
   * bytes, no transcript — settings + counters only.
   */
  captureDiagnostics(): Record<string, unknown> {
    const track = this.mediaStream?.getAudioTracks()[0]
    const settings = track?.getSettings?.() ?? {}
    return {
      // P4S-31D1-F: RMS + liveness now sourced from the controller's metering
      // AnalyserNode (via setMeterRms), not the removed capture ScriptProcessor.
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
      capturing: this.mediaStream !== null,
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
    // P4S31: no bare 'mic_stop' control frame — the governed WS uses the GAP F
    // terminator inside transcribeUtterance(). stopMic only tears down capture.
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
   * P4S31 Voice Convergence — GAP F wire protocol.
   *
   * Stream one utterance to the governed voice WS and resolve with the first
   * final transcript (or an error frame). Protocol, in order:
   *   1. a TEXT JSON control frame:
   *      {source, device_registry_id, consent_grant_id, content_type, activation_mode}
   *   2. the raw PCM16 audio as BINARY chunks
   *   3. a text {"type":"end"} terminator
   * The server relays a typed `transcript` frame or a canonical `error` frame
   * ({type:"error", code:<VoiceErrorCode>}). This replaces the old bare
   * per-frame control burst — one governed protocol for every surface.
   */
  transcribeUtterance(
    pcmChunks: ArrayBuffer[],
    control: {
      source: string
      deviceRegistryId: string
      consentGrantId: string
      activationMode?: string
    },
    timeoutMs = 15_000,
  ): Promise<{ ok: true; text: string } | { ok: false; code: string }> {
    return new Promise((resolve) => {
      let settled = false
      const done = (r: { ok: true; text: string } | { ok: false; code: string }) => {
        if (settled) return
        settled = true
        offTranscript()
        offError()
        clearTimeout(timer)
        resolve(r)
      }
      const offTranscript = this.ws.on('transcript', (data) => {
        const text = (data.text as string) ?? ''
        const isFinal = data.final as boolean
        if (isFinal && text.trim()) done({ ok: true, text })
      })
      // Canonical error frames carry an UPPERCASE VoiceErrorCode in `code`; relay
      // it verbatim (no client remapping — that is the convergence contract).
      const offError = this.ws.on('error', (data) => {
        done({ ok: false, code: (data.code as string) || 'STT_FAILED' })
      })
      const timer = setTimeout(() => done({ ok: false, code: 'TIMEOUT' }), timeoutMs)

      try {
        // 1. control frame (TEXT JSON, MUST be first)
        this.ws.sendRaw(
          JSON.stringify({
            source: control.source,
            device_registry_id: control.deviceRegistryId,
            consent_grant_id: control.consentGrantId,
            content_type: RAW_PCM_CONTENT_TYPE,
            activation_mode: control.activationMode ?? 'push_to_talk',
          }),
        )
        // 2. binary audio chunks
        for (const buf of pcmChunks) this.ws.sendBinary(buf)
        // 3. terminator
        this.ws.sendRaw(JSON.stringify({ type: 'end' }))
      } catch {
        done({ ok: false, code: 'RUNTIME_UNAVAILABLE' })
      }
    })
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
