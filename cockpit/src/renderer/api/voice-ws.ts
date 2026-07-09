import { WsClient } from './websocket'
import { acquireClerkToken } from './client'
import {
  playTtsAudio,
  cancelPlayback,
  setPlaybackCallbacks,
} from './tts-playback-controller'

/** Canonical typed voice-WS connect failure codes (P4S-VOICE-WS-AUTH-PREFLIGHT-001).
 *  A subset of the voiceStore VoiceOutcome union — the ones connect() can produce. */
export type VoiceWsErrorCode =
  | 'VOICE_WS_AUTH_TOKEN_MISSING'
  | 'VOICE_WS_AUTH_TOKEN_TIMEOUT'
  | 'VOICE_WS_AUTH_FAILED'
  | 'VOICE_WS_UPGRADE_FAILED'
  | 'VOICE_RUNTIME_TIMEOUT'

/** Error carrying a canonical code so the adapter labels the exact failing boundary
 *  instead of a generic "unreachable". */
export class VoiceWsError extends Error {
  constructor(public code: VoiceWsErrorCode, message?: string) {
    super(message ?? code)
    this.name = 'VoiceWsError'
  }
}

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

// SEPARATE CLOCKS (P4S-VOICE-WS-AUTH-PREFLIGHT-001). The token fetch and the WS
// connect each have their OWN budget, and BOTH must finish inside the adapter's
// outer 8s voice-start watchdog (CONSENT_START_TIMEOUT_MS). 3 + 5 = 8 ceiling, but
// the token timer fails FAST and TYPED so the WS timer + outer watchdog are never
// the ones that surface a token stall.
const TOKEN_ACQUIRE_BUDGET_MS = 3000
const WS_CONNECT_TIMEOUT_MS = 5000

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

/**
 * P4S31 SINGLE-ACQUISITION MODEL (permanent mobile fix).
 *
 * The mic is opened with getUserMedia EXACTLY ONCE per capture, on the user
 * gesture, and that ONE live MediaStream is reused for the whole turn. The old
 * design called getUserMedia twice — a permission probe (then .stop()) followed
 * by a second acquisition in startMic. On iOS Safari the second call contends
 * with the OS audio session the first just released and HANGS forever ("Requesting
 * mic…" that never loads). Acquiring once removes the contention at the root.
 *
 * The gesture-fresh stream is cached here so the permission layer (which fires on
 * the tap) and startMic (which runs after the consent round-trip) share the SAME
 * stream instead of each opening their own.
 */
let _gestureStream: MediaStream | null = null

/** Open the mic once, on the gesture, bounded by a timeout so a stalled
 *  getUserMedia degrades to a typed MicAcquireTimeout instead of a dead button. */
async function _acquireMicOnce(constraints: MediaStreamConstraints): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw Object.assign(
      new Error('Browser does not support microphone capture'),
      { name: 'NotSupportedError' },
    )
  }
  let timer: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(Object.assign(
        new Error('Microphone did not open — close other mic apps/tabs and try again'),
        { name: 'MicAcquireTimeout' },
      ))
    }, MIC_ACQUIRE_TIMEOUT_MS)
  })
  try {
    return await Promise.race([
      navigator.mediaDevices.getUserMedia(constraints),
      timeout,
    ])
  } finally {
    if (timer) clearTimeout(timer)
  }
}

/**
 * FIRST consent layer — the browser mic permission, surfaced up front so the
 * single mic-tap handler can, on its success, request the UMH push_to_talk grant
 * WITHOUT a second user tap (single-gesture consent). CRITICALLY: this acquires
 * the ONE capture stream and KEEPS it live (cached in `_gestureStream`) — it does
 * NOT stop it. startMic() then reuses this exact stream, so there is never a
 * second getUserMedia to contend/hang on iOS.
 *
 * Rejects with the original getUserMedia error (name preserved: NotAllowedError /
 * NotFoundError / NotSupportedError / MicAcquireTimeout) so callers can branch on
 * a denied browser permission vs a failed server grant vs a stalled acquisition.
 */
export async function ensureBrowserMicPermission(): Promise<void> {
  log('browser_mic_permission_acquire')
  // If a live gesture stream is already open (e.g. a prior stage in the same
  // tap), reuse it — never open a second one.
  if (_gestureStream && _gestureStream.getAudioTracks().some((t) => t.readyState === 'live')) {
    log('browser_mic_permission_stream_reused')
    return
  }
  _gestureStream = await _acquireMicOnce({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      sampleRate: TARGET_SAMPLE_RATE,
    },
  })
  log('browser_mic_permission_granted')
}

/**
 * Release the gesture-acquired mic stream WITHOUT starting capture. Called on any
 * path that opened the mic (ensureBrowserMicPermission) but then aborts before
 * startMic hands the stream to the recorder (e.g. the consent grant is refused) —
 * so the mic indicator doesn't stay on and iOS doesn't hold a leaked session.
 */
export function releaseGestureStream(): void {
  if (_gestureStream) {
    _gestureStream.getTracks().forEach((t) => t.stop())
    _gestureStream = null
    log('gesture_stream_released')
  }
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
    // Built with no auth here; connect() REBUILDS it with the Clerk bearer
    // subprotocol (the token isn't available synchronously). autoReconnect:false —
    // the voice WS is REQUEST-SCOPED (one utterance per connection, the server
    // closes after the transcript); auto-reconnect would storm 4002s.
    this.ws = this._buildClient(undefined)
  }

  /** Build the underlying WsClient with the given subprotocols + wire the binary
   *  handler. Centralized so connect() can rebuild it with a fresh auth token. */
  private _buildClient(protocols: string[] | undefined): WsClient {
    const c = new WsClient(VOICE_URL, protocols, { autoReconnect: false })
    c.onBinary((buf) => this._queueAudio(buf))
    return c
  }

  async connect(): Promise<void> {
    log('ws_connect', VOICE_URL)
    // CRITICAL: the governed voice WS requires Clerk auth. A browser WebSocket can't
    // set an Authorization header, so — like the persistent event WS
    // (useOrganismRealtime) — the token rides as a `bearer.<jwt>` subprotocol
    // (server: validate_ws_clerk_token option 2).
    //
    // SEPARATE CLOCKS (P4S-VOICE-WS-AUTH-PREFLIGHT-001): the token fetch has its OWN
    // hard budget (token_acquire_timer, ~3s) DISTINCT from the WS connect timer (5s).
    // The previous code fetched the token UNBOUNDED and BEFORE the WS timer armed, so
    // a mobile-Safari token stall consumed the whole voice-start budget and the outer
    // 8s watchdog fired a FALSE "server unreachable". Now a token stall fails FAST and
    // TYPED (VOICE_WS_AUTH_TOKEN_TIMEOUT) before either watchdog — via the bounded
    // acquireClerkToken() accessor (Gate 14 blocks any raw unbounded fetch here).
    const auth = await acquireClerkToken(TOKEN_ACQUIRE_BUDGET_MS)
    if (auth.status === 'timeout') {
      log('ws_token_timeout', 'clerk getToken stalled past budget')
      throw new VoiceWsError('VOICE_WS_AUTH_TOKEN_TIMEOUT', 'Sign-in token timed out')
    }
    if (auth.status === 'missing') {
      log('ws_token_missing', 'no clerk token — not signed in')
      throw new VoiceWsError('VOICE_WS_AUTH_TOKEN_MISSING', 'Not signed in')
    }
    const protocols = [`bearer.${auth.token}`]

    // Token is known-good; NOW build the socket and arm the WS connect timer.
    this.ws.disconnect()
    this.ws = this._buildClient(protocols)
    return new Promise<void>((resolve, reject) => {
      const onConnected = this.ws.on('connected', () => {
        log('ws_connected')
        onConnected()
        onDisconnected()
        clearTimeout(timer)
        resolve()
      })
      const onDisconnected = this.ws.on('disconnected', () => {
        log('ws_connect_failed', 'disconnected during connect')
        onConnected()
        onDisconnected()
        clearTimeout(timer)
        // The socket closed/errored BEFORE it ever opened. With a valid token this is
        // the server rejecting the upgrade (auth 4001/403) — a distinct boundary from
        // a stalled socket. Classify as UPGRADE_FAILED (adapter refines to AUTH_FAILED
        // when it knows the token was sent).
        reject(new VoiceWsError('VOICE_WS_UPGRADE_FAILED', 'Voice server closed the connection during connect'))
      })
      const timer = setTimeout(() => {
        onConnected()
        onDisconnected()
        log('ws_connect_timeout', 'ws_connect_timer elapsed')
        // ROOT B: close the underlying socket before rejecting. Otherwise the
        // WsClient keeps shouldReconnect=true and its heartbeat/visibility
        // listeners, so a socket that opens AFTER the timeout becomes an
        // orphaned, forever-reconnecting zombie with no owning reference.
        this.ws.disconnect()
        // Socket neither opened nor closed within the WS budget → the runtime never
        // became ready. Distinct from a token stall (already handled above).
        reject(new VoiceWsError('VOICE_RUNTIME_TIMEOUT', 'Voice server did not respond'))
      }, WS_CONNECT_TIMEOUT_MS)
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
    log('mic_reuse_gesture_stream')

    // P4S31 SINGLE-ACQUISITION: reuse the ONE stream opened on the gesture by
    // ensureBrowserMicPermission — NEVER call getUserMedia a second time (that
    // second call is what hangs on iOS Safari). If no gesture stream is live
    // (returning device where the permission layer short-circuited, or a direct
    // caller), acquire once here, bounded by the same timeout.
    let stream: MediaStream
    if (_gestureStream && _gestureStream.getAudioTracks().some((t) => t.readyState === 'live')) {
      stream = _gestureStream
      log('mic_gesture_stream_live')
    } else {
      stream = await _acquireMicOnce({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: TARGET_SAMPLE_RATE,
        },
      })
      _gestureStream = stream
    }

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
    // P4S31 SINGLE-ACQUISITION: the gesture stream IS this.mediaStream — clear the
    // shared cache too so the NEXT tap opens a fresh stream, never reuses a dead one.
    _gestureStream = null
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
      /** Wire content_type. Defaults to raw PCM16 (live-mic lane). Pass the blob's
       *  real container type (e.g. audio/mp4) to take the server ffmpeg-decode
       *  lane — needed on iOS Safari, whose decodeAudioData can't decode its own
       *  MediaRecorder mp4 output. */
      contentType?: string
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
            content_type: control.contentType ?? RAW_PCM_CONTENT_TYPE,
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
