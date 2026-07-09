/**
 * voice-controller — P4S-31D1-B voice-MESSAGE flow (lanes C+D+E).
 *
 * Recording produces a reviewable VoiceMessageDraft, NEVER a chat message.
 * The D1-A auto-dispatch (transcript pushed into chat on silence / tap-to-stop)
 * is REPLACED: this controller finalizes a draft to review; the ONLY path into
 * Cockpit Chat is the operator's explicit send, which lives in
 * voiceMessageStore.sendDraft → chatStore.addVoiceTranscript →
 * sendMessage(text, 'voice', …). No addVoiceTranscript call exists here.
 *
 * Responsibilities:
 *  - open capture (PCM16 WS + a parallel MediaRecorder on the SAME MediaStream)
 *  - create/drive a draft in useVoiceMessageStore
 *  - VAD finalization off VAD_CONFIG (Lane D): intra-utterance pauses ignored,
 *    continuous silence / manual tap / max-duration finalizes to review
 *  - notifyVoiceMessageSent: arm the TTS/held-message presentation on send
 *  - retryDraftTranscription (Lane E): re-run STT over the preserved audio blob
 *  - abortActiveRecording: tear the mic/recorder down with no dispatch
 */
import { VoiceWsClient, releaseGestureStream, VoiceWsError } from './voice-ws'
import type { VoiceOutcome } from '../stores/voiceStore'

/** Map a voice-WS connect failure to a canonical typed outcome + a precise,
 *  non-generic banner string (P4S-VOICE-WS-AUTH-PREFLIGHT-001). A token/auth failure
 *  must NEVER surface as "server unreachable" — the server is reachable; the client
 *  couldn't authenticate. */
function classifyVoiceWsError(err: unknown): { outcome: VoiceOutcome; message: string } {
  if (err instanceof VoiceWsError) {
    switch (err.code) {
      case 'VOICE_WS_AUTH_TOKEN_TIMEOUT':
        return { outcome: 'VOICE_WS_AUTH_TOKEN_TIMEOUT', message: 'Sign-in timed out — tap the mic to try again' }
      case 'VOICE_WS_AUTH_TOKEN_MISSING':
        return { outcome: 'VOICE_WS_AUTH_TOKEN_MISSING', message: 'Please sign in to use voice' }
      case 'VOICE_WS_UPGRADE_FAILED':
        // socket closed before opening WITH a valid token → server rejected auth
        return { outcome: 'VOICE_WS_AUTH_FAILED', message: 'Voice sign-in was rejected — try again' }
      case 'VOICE_RUNTIME_TIMEOUT':
        return { outcome: 'VOICE_RUNTIME_TIMEOUT', message: 'Voice server did not respond — try again' }
    }
  }
  // Unknown/unexpected — a genuine reach failure is the only honest generic here.
  return { outcome: 'VOICE_WS_UNAVAILABLE', message: 'Voice server unavailable — check connection' }
}
import { voiceConsentForCapture } from './platform-voice-adapter'
import { VOICE_ERROR_CODES } from './voiceErrorCodes'
import { useVoiceStore } from '../stores/voiceStore'
import { useChatStore } from '../stores/chatStore'
import { useVoiceMessageStore, VAD_CONFIG } from '../stores/voiceMessageStore'
import { unlockAudioForIOS, setPlaybackCallbacks, cancelPlayback, resetPlayback } from './tts-playback-controller'
import { createTurn, updatePartial, cancelTurn, getCurrentTurn } from './voice-turn-assembler'
import { diagStage, diagFlush } from './voice-diag'

/**
 * P4S-31D1-E artifact-binding error taxonomy. The locally-captured MediaRecorder
 * blob is the SINGLE SOURCE OF TRUTH for transcription — not just playback. When
 * transcription cannot proceed, we emit ONE of these DISTINCT codes into the
 * draft error so the operator sees the real cause. These NEVER collapse to a
 * bare missing-audio claim while a playable blob exists locally.
 *
 * Naming note: the D1-E packet refers to the draft object as `VoiceNoteDraft`.
 * That is the SAME object as `VoiceMessageDraft` in voiceMessageStore.ts — a doc
 * alias only. Do NOT rename the store type; `VoiceNoteDraft == VoiceMessageDraft`.
 */
// P4S31 Voice Convergence: the four codes that also exist server-side
// (EMPTY_AUDIO_BLOB, UNSUPPORTED_AUDIO_FORMAT, DECODE_FAILED, STT_FAILED) now
// REFERENCE the canonical, codegen'd VOICE_ERROR_CODES mirror — one source of
// truth, so client and server can never disagree. The four CLIENT-ONLY codes
// below are pre-flight binding checks that fire BEFORE any audio reaches the
// server (a missing artifact ref, a null blob, etc.) and have no server code.
export const VOICE_ARTIFACT_ERROR = {
  // ── client-only pre-flight binding checks (retained) ──
  /** Blob exists (size>0) but nothing was streamed to the voice WS. */
  LOCAL_AUDIO_PRESENT_UPLOAD_MISSING: 'LOCAL_AUDIO_PRESENT_UPLOAD_MISSING',
  /** PCM was streamed but the server saw 0 bytes / no audio energy. */
  LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY: 'LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY',
  /** The referenced audio artifact could not be located for transcription. */
  AUDIO_ARTIFACT_REF_NOT_FOUND: 'AUDIO_ARTIFACT_REF_NOT_FOUND',
  /** The draft carried no audio field at all (blob null). */
  MISSING_AUDIO_FIELD: 'MISSING_AUDIO_FIELD',
  // ── canonical codes, sourced from the ONE server taxonomy (no remap) ──
  EMPTY_AUDIO_BLOB: VOICE_ERROR_CODES.EMPTY_AUDIO_BLOB,
  UNSUPPORTED_AUDIO_FORMAT: VOICE_ERROR_CODES.UNSUPPORTED_AUDIO_FORMAT,
  DECODE_FAILED: VOICE_ERROR_CODES.DECODE_FAILED,
  STT_FAILED: VOICE_ERROR_CODES.STT_FAILED,
} as const

export type VoiceArtifactErrorCode = keyof typeof VOICE_ARTIFACT_ERROR

let client: VoiceWsClient | null = null
let cleanups: (() => void)[] = []
let chatUnsub: (() => void) | null = null
/** ~10Hz poll that mirrors client.clientRms into the message store (the meter). */
let meterInterval: ReturnType<typeof setInterval> | null = null
/** Wall-clock ms the meter started, for the "mic appears silent" hint. */
let meterStartedAt = 0
let heldVoiceMessage: { id: string; content: string } | null = null
/** The voice turn ID for the currently pending voice response. */
let _pendingVoiceTurnId: string | null = null

// ── Recording session (draft) state ──────────────────────────────────────────
// P4S-31D1-F BLOB-ONLY: the note rail captures with ONE mechanism — MediaRecorder
// (the playable blob = the sole transcription artifact). There is no live PCM
// stream, so there is no client-side VAD (sawSpeech/silence windows) and no
// live-WS "fast path" transcript. Recording stops on tap-to-stop + the 120s hard
// cap; transcription is always _transcribeBlob on finalize.
let recorder: MediaRecorder | null = null
let recorderChunks: Blob[] = []
let recordingStartedAt = 0
let onRecorderStop: ((blob: Blob | null) => void) | null = null
/** ROOT D (iOS): the current capture stream, kept so teardownCapture can detach
 *  its track health handlers even on paths where recorder.onstop never fires. */
let captureStream: MediaStream | null = null

// P3 — the current capture as ONE object. Replaces the bare `finalizing` latch
// (which stranded when an exit path forgot to reset it) and the "read the live
// activeDraftId" pattern (which wrote a returning transcript onto the WRONG draft
// after a concurrent delete/new-recording). `draftId` is CAPTURED here at capture
// start and used by every completion handler; `done` is the finalize latch and is
// cleared in a `finally`, so it can never strand. null = no capture in flight.
interface CaptureSession {
  id: string
  draftId: string
  turnId: string
  done: boolean
}
let activeSession: CaptureSession | null = null
let _sessionSeq = 0
/** ROOT F: true only while a transcribeUtterance round-trip owns the WS error
 *  channel — the top-level error handler must not also stamp the draft failed
 *  (that double-write loses the precise code the scoped listener returns). */
let transcribeInFlight = false

// Metering AnalyserNode (meter-ONLY: RMS bar + silent-mic hint). No VAD, no
// finalize — it can never re-introduce the two-path divergence bug class.
let meterAudioContext: AudioContext | null = null
let meterAnalyser: AnalyserNode | null = null
let meterSource: MediaStreamAudioSourceNode | null = null
let meterRafId: number | null = null

const PENDING_RESPONSE_TIMEOUT_MS = 30_000
const TTS_GENERATE_TIMEOUT_MS = 15_000
/** ROOT A: max time micState may sit at transcribing/processing before we force
 *  idle. Bound to the WS transcribe timeout (25s) + margin so a real slow STT
 *  resolves first and this only fires on a genuine hang. */
const MIC_STATE_WATCHDOG_MS = 35_000
/** Meter poll cadence — ~10Hz is enough to look live and stays cheap. */
const METER_POLL_MS = 100
/** Peak RMS below this after MIC_SILENT_HINT_MS means the mic looks silent. */
const MIC_SILENT_RMS_FLOOR = 0.005
/** How long capture may stay flat-at-0 before we surface the silent-mic hint. */
const MIC_SILENT_HINT_MS = 2_000

const log = (stage: string, ...args: unknown[]) => {
  console.log(`[VoicePipeline] ${stage}`, ...args)
  // P4S-VOICE-CLIENT-DIAG: mirror every stage into the diag timeline so a
  // client-side stall (which never reaches the server) is still observable server-side.
  diagStage(stage, args.length ? String(args[0]) : '')
}

// P1 — session timer registry. A single owner for every capture/turn timeout.
// `arm(key, …)` ALWAYS clears the prior handle for that key before setting the
// new one, so a timer can never be orphaned by re-arming (the double-send
// `pendingTimeout` leak class). Keys used: 'pendingResponse', 'maxRecording',
// 'ttsGenerate'. `clearAll()` replaces the old `clearAllTimers()`.
const _timers = new Map<string, ReturnType<typeof setTimeout>>()
const sessionTimers = {
  arm(key: string, fn: () => void, ms: number): void {
    const prev = _timers.get(key)
    if (prev) clearTimeout(prev)
    _timers.set(key, setTimeout(() => { _timers.delete(key); fn() }, ms))
  },
  clear(key: string): void {
    const t = _timers.get(key)
    if (t) { clearTimeout(t); _timers.delete(key) }
  },
  clearAll(): void {
    for (const t of _timers.values()) clearTimeout(t)
    _timers.clear()
  },
}

/**
 * Start the ~10Hz capture meter: mirror client.clientRms into the message store
 * so the recording card shows a live audio-level bar. Cheap (one getter read +
 * one shallow store write per tick); no render loop, no FFT. The card reads the
 * store field. Cleared on stop / finalize / abort.
 */
function startCaptureMeter(): void {
  stopCaptureMeter()
  meterStartedAt = Date.now()
  useVoiceMessageStore.getState().resetCaptureMeter()
  meterInterval = setInterval(() => {
    if (!client) return
    const rms = client.clientRms
    const elapsed = Date.now() - meterStartedAt
    // ROOT D (iOS): the RMS is only trustworthy when the meter AudioContext is
    // actually 'running'. On iOS Safari an AudioContext created outside the user
    // gesture (which is where we are — many awaits past the tap) starts
    // 'suspended', .resume() is ignored, and the analyser reads all-zeros. Without
    // this gate that produced a FALSE "mic appears silent" hint on EVERY iOS
    // recording even while the user spoke normally (the blob itself records fine).
    // If the context isn't running, RMS is unreliable → never emit the hint.
    const meterRunning = meterAudioContext?.state === 'running'
    // silentMs: elapsed only counts toward the hint once we're past the grace
    // window, the meter is trustworthy, AND the session never rose above the floor.
    const peak = useVoiceMessageStore.getState().captureRmsPeak
    const silentMs =
      meterRunning &&
      elapsed >= MIC_SILENT_HINT_MS &&
      Math.max(peak, rms) < MIC_SILENT_RMS_FLOOR
        ? elapsed
        : 0
    useVoiceMessageStore.getState().setCaptureRms(rms, silentMs)
  }, METER_POLL_MS)
}

function stopCaptureMeter(): void {
  if (meterInterval) { clearInterval(meterInterval); meterInterval = null }
  meterStartedAt = 0
  useVoiceMessageStore.getState().resetCaptureMeter()
}

/**
 * P4S-31D1-F: meter-ONLY AnalyserNode on the capture MediaStream. Computes RMS
 * (0..1) at display cadence and pushes it into the WS client (setMeterRms), which
 * the ~10Hz `startCaptureMeter` poll reads via `client.clientRms`. This replaces
 * the removed capture ScriptProcessor as the "is the mic actually hearing me"
 * source. NO VAD, NO finalize, and NOT connected to destination (no echo).
 * iOS-safe: the AudioContext is created + resumed inside the recording gesture.
 * `getFloatTimeDomainData` yields −1..1 samples so sqrt(meanSquare) is the same
 * 0..1 metric MIC_SILENT_RMS_FLOOR / VAD_CONFIG thresholds are calibrated for.
 */
function startMeterAnalyser(stream: MediaStream): void {
  stopMeterAnalyser()
  try {
    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!AudioCtx) { log('meter_analyser_unavailable'); return }
    meterAudioContext = new AudioCtx()
    if (meterAudioContext.state === 'suspended') void meterAudioContext.resume()
    log('meter_audio_context_state', meterAudioContext.state)
    meterSource = meterAudioContext.createMediaStreamSource(stream)
    meterAnalyser = meterAudioContext.createAnalyser()
    meterAnalyser.fftSize = 1024
    meterSource.connect(meterAnalyser) // NOT connected to destination — no echo
    const buf = new Float32Array(meterAnalyser.fftSize)
    const tick = (): void => {
      if (!meterAnalyser) return
      meterAnalyser.getFloatTimeDomainData(buf)
      let sumSq = 0
      for (let i = 0; i < buf.length; i++) sumSq += buf[i] * buf[i]
      const rms = buf.length ? Math.sqrt(sumSq / buf.length) : 0
      client?.setMeterRms(rms) // → client.clientRms → startCaptureMeter poll → CaptureMeter
      meterRafId = requestAnimationFrame(tick)
    }
    meterRafId = requestAnimationFrame(tick)
  } catch (e) {
    log('meter_analyser_start_failed', e)
  }
}

function stopMeterAnalyser(): void {
  if (meterRafId !== null) { cancelAnimationFrame(meterRafId); meterRafId = null }
  meterSource?.disconnect()
  meterAnalyser?.disconnect()
  meterSource = null
  meterAnalyser = null
  if (meterAudioContext && meterAudioContext.state !== 'closed') void meterAudioContext.close()
  meterAudioContext = null
  client?.setMeterRms(0)
}

// P2 — the SINGLE owner of capture-resource teardown. Every abort/stop/destroy
// path routes its resource cleanup through here instead of re-listing the steps,
// so no path can forget one. This is also the only place `releaseGestureStream()`
// is wired on the controller side — previously it had ZERO controller callers, so
// an abort-before-startMic left the getUserMedia stream live (iOS mic stayed lit).
// This owns RESOURCES only; callers still own their own state/flag transitions.
function teardownCapture(): void {
  _stopRecorder(() => { /* discard */ })
  // ROOT D (iOS): detach the track mute/ended health handlers so they can't fire
  // across sessions (on abort/error paths recorder.onstop may never run).
  if (captureStream) { _detachTrackHandlers(captureStream); captureStream = null }
  stopMeterAnalyser()
  stopCaptureMeter()
  client?.stopMic()
  releaseGestureStream()
  sessionTimers.clearAll()
}

// ── MediaRecorder lifecycle ──────────────────────────────────────────────────

function _pickRecorderMime(): string {
  // Desktop Chrome/Firefox support webm/opus; iOS Safari supports NONE of those
  // and only records audio/mp4 (AAC). Include the mp4 candidates so mobile picks
  // an EXPLICIT supported type rather than falling to MediaRecorder's unlabeled
  // default (which the content-type/extension logic would then mislabel).
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4;codecs=mp4a.40.2', // AAC-LC in mp4 — iOS Safari
    'audio/mp4',
    'audio/wav',
  ]
  if (typeof MediaRecorder === 'undefined' || typeof MediaRecorder.isTypeSupported !== 'function') {
    return ''
  }
  for (const c of candidates) {
    if (MediaRecorder.isTypeSupported(c)) return c
  }
  return ''
}

function _startRecorder(stream: MediaStream): void {
  recorderChunks = []
  onRecorderStop = null
  captureStream = stream
  if (typeof MediaRecorder === 'undefined') {
    log('media_recorder_unavailable')
    recorder = null
    return
  }
  try {
    const mime = _pickRecorderMime()
    const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream)
    recorder = rec
    // Capture the effective mimeType in the closure so blob assembly stays correct
    // even after `recorder` is nulled and rec's handlers are detached (below).
    const recMime = rec.mimeType
    rec.ondataavailable = (e: BlobEvent) => {
      if (e.data && e.data.size > 0) recorderChunks.push(e.data)
    }
    rec.onstop = () => {
      const type = recMime || recorderChunks[0]?.type || 'audio/webm'
      const blob = recorderChunks.length > 0 ? new Blob(recorderChunks, { type }) : null
      const cb = onRecorderStop
      onRecorderStop = null
      // ROOT B: detach THIS recorder's handlers now that its final blob is
      // delivered. Prevents a late/stray ondataavailable from the OLD recorder
      // pushing a tail chunk into the NEXT session's recorderChunks (cross-session
      // contamination) — the handlers close over the shared module-level array.
      rec.ondataavailable = null
      rec.onstop = null
      _detachTrackHandlers(stream)
      if (cb) cb(blob)
    }
    // ROOT D (iOS): a MediaRecorder error (e.g. the OS tearing down the audio
    // session on a call/Siri interruption) must not hang the draft at
    // 'transcribing' — tear down gracefully so the mic returns to idle.
    rec.onerror = (e) => {
      log('recorder_error', e)
      abortActiveRecording()
    }
    // ROOT D (iOS): on screen-lock / backgrounding, iOS fires mute/ended on the
    // capture track and stops feeding the recorder. Detect it and finalize the
    // audio captured so far (D3's timeslice means chunks are already flushed)
    // rather than losing everything or hanging. If nothing was captured, abort.
    _wireTrackHealth(stream)
    // ROOT D (iOS): a 1s timeslice flushes `ondataavailable` periodically. Without
    // it, MediaRecorder emits exactly ONE dataavailable at stop() — so any iOS
    // interruption before a clean stop() loses ALL audio. With it, recorderChunks
    // holds the flushed data even when onstop never fires cleanly. The timeslice
    // only changes chunk cadence; the container/mimeType is fixed at construction,
    // so the playable bubble + server ffmpeg decode are unaffected.
    rec.start(1000)
    log('recorder_started', rec.mimeType)
  } catch (e) {
    log('recorder_start_failed', e)
    recorder = null
  }
}

/** ROOT D (iOS): wire mute/ended on each audio track so an OS-driven capture
 *  teardown (screen-lock, call, backgrounding) finalizes gracefully instead of
 *  hanging the draft at 'transcribing' or silently losing the recording. */
function _wireTrackHealth(stream: MediaStream): void {
  for (const track of stream.getAudioTracks()) {
    const onInterrupt = (evt: string) => {
      log('capture_track_interrupted', evt, track.readyState)
      // Only act on a live capture — ignore events during teardown.
      if (!activeSession || activeSession.done) return
      if (recorder && recorder.state !== 'inactive') {
        // Audio was being captured (and, with the timeslice, flushed) — preserve it.
        _finalizeRecording('manual_stop')
      } else {
        abortActiveRecording()
      }
    }
    track.onended = () => onInterrupt('ended')
    track.onmute = () => onInterrupt('mute')
  }
}

/** Detach the track health handlers so they can't fire across sessions. */
function _detachTrackHandlers(stream: MediaStream): void {
  for (const track of stream.getAudioTracks()) {
    track.onended = null
    track.onmute = null
  }
}

/** Stop the recorder and deliver the assembled blob to `cb` (null if none). */
function _stopRecorder(cb: (blob: Blob | null) => void): void {
  const rec = recorder
  if (rec && rec.state !== 'inactive') {
    onRecorderStop = cb
    try {
      rec.stop() // onstop delivers the blob AND detaches rec's handlers
    } catch {
      onRecorderStop = null
      // onstop won't fire — detach here so a stray ondataavailable can't leak.
      rec.ondataavailable = null
      rec.onstop = null
      cb(null)
    }
  } else {
    // Already inactive: onstop already fired (and detached). Detach defensively
    // in case a recorder was inactive-at-entry with handlers still attached.
    if (rec) { rec.ondataavailable = null; rec.onstop = null }
    cb(null)
  }
  recorder = null
}

// ── Draft finalization (Lane D) ──────────────────────────────────────────────

/**
 * Finalize the active recording into a review draft. Stops the MediaRecorder,
 * moves the draft to transcribing, attaches the captured audio, and hands the
 * still-pending final WS transcript off to `completeActiveTranscript`.
 * NEVER dispatches to chat — that is only ever the operator's explicit send.
 */
function _finalizeRecording(finalizedBy: 'manual_stop' | 'silence_timeout'): void {
  // P3 re-entrancy guard: a finalize already ran/running for this session → no-op.
  // (Replaces the bare `finalizing` latch; delete-during-finalize + max-timeout-vs-
  // manual-stop can no longer double-finalize.)
  const session = activeSession
  if (!session || session.done) {
    log('finalize_ignored_no_session_or_done')
    return
  }
  session.done = true
  sessionTimers.clearAll()
  stopCaptureMeter()
  stopMeterAnalyser()

  const now = Date.now()
  const durationMs = recordingStartedAt ? now - recordingStartedAt : 0
  // ROOT F: the draft id is CAPTURED from the session, fixed for this whole
  // finalize — every completion writes to THIS draft, never the live activeDraftId
  // (which a concurrent delete/new-recording may have nulled or rebound).
  const draftId = session.draftId

  // Guarantee terminal resolution even if a branch throws or falls through: the
  // finally forces micState back to a terminal state so the mic can never strand
  // at 'transcribing'. Async work (the blob transcribe) resolves its own micState.
  let asyncPending = false
  try {
    useVoiceMessageStore.getState().finalizeActiveDraft(finalizedBy, durationMs, null, now)
    _armMicStateWatchdog() // ROOT A: transcribing must not hang forever
    useVoiceStore.getState().setMicState('transcribing')

    if (client) client.stopMic()

    _stopRecorder((blob) => {
      if (blob) useVoiceMessageStore.getState().attachAudio(blob)

      // No usable blob → recoverable missing/empty draft, NEVER a chat message.
      if (!blob || blob.size <= 0) {
        if (draftId) {
          const code = !blob
            ? VOICE_ARTIFACT_ERROR.MISSING_AUDIO_FIELD
            : VOICE_ARTIFACT_ERROR.EMPTY_AUDIO_BLOB
          useVoiceMessageStore.getState().markFailed(draftId, code)
        } else {
          useVoiceMessageStore.getState().markNoSpeech()
        }
        _resolveMicIdle()
        log('recording_no_usable_blob', `duration=${durationMs}`)
        return
      }

      // BLOB SOURCE-OF-TRUTH (the only transcription path).
      if (draftId) {
        asyncPending = true
        transcribeInFlight = true
        void _transcribeBlob(draftId, blob)
          .then((res) => {
            if (res.ok) {
              useVoiceMessageStore.getState().completeTranscript(draftId, res.text, res.confidence)
            } else {
              const FINALIZE_CODE: Record<string, string> = {
                WS_UNAVAILABLE: 'STT_FAILED',
                DECODE_FAILED: VOICE_ARTIFACT_ERROR.DECODE_FAILED,
                STT_FAILED: VOICE_ARTIFACT_ERROR.STT_FAILED,
                TIMEOUT: 'STT_FAILED',
                LOCAL_AUDIO_PRESENT_UPLOAD_MISSING: VOICE_ARTIFACT_ERROR.LOCAL_AUDIO_PRESENT_UPLOAD_MISSING,
                LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY: VOICE_ARTIFACT_ERROR.LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY,
              }
              useVoiceMessageStore.getState().markFailed(draftId, FINALIZE_CODE[res.code] ?? res.code)
            }
          })
          .finally(() => {
            transcribeInFlight = false
            _resolveMicIdle() // ROOT A: transcribing ALWAYS resolves to idle
          })
      } else {
        _resolveMicIdle()
      }
    })
  } finally {
    // If nothing async is pending, the mic must already be terminal here. The
    // async path resolves micState in its own .finally above. Either way,
    // 'transcribing' can never latch forever.
    if (!asyncPending) _resolveMicIdle()
  }
  log('recording_finalized', finalizedBy, `duration=${durationMs}`)
}

/** ROOT A: force micState to a terminal 'idle' + clear the transcribing watchdog.
 *  Safe to call more than once. Does not clobber a live NEW recording's state. */
function _resolveMicIdle(): void {
  sessionTimers.clear('micStateWatchdog')
  const vs = useVoiceStore.getState()
  const s = vs.micState
  // Only force idle from the terminal-ish states this finalize owns. A concurrent
  // fresh capture may already be 'listening'/'recording'/'requesting_permission' —
  // never yank that back to idle.
  if (s === 'transcribing' || s === 'processing') vs.setMicState('idle')
}

/** ROOT A: a hard watchdog so micState can NEVER hang at transcribing/processing.
 *  If still stuck after the window, force idle + a terminal outcome. */
function _armMicStateWatchdog(): void {
  sessionTimers.arm('micStateWatchdog', () => {
    const vs = useVoiceStore.getState()
    if (vs.micState === 'transcribing' || vs.micState === 'processing') {
      log('mic_state_watchdog_forced_idle', vs.micState)
      vs.setMicState('idle')
      vs.setLastOutcome('TIMEOUT')
    }
  }, MIC_STATE_WATCHDOG_MS)
}

/** Return a wired VoiceWsClient WITHOUT connecting the socket. Used by startVoice so
 *  mic acquisition + recording can proceed with the socket still CLOSED — the WS is
 *  only opened at finalize (_transcribeBlob → ensureClient). This is what removes the
 *  accepted-but-frameless idle-socket window (P4S-VOICE-WS-FRAMELESS-SOCKET-002). If a
 *  live connected client already exists, reuse it; otherwise (re)build a fresh,
 *  disconnected one. */
function getOrCreateClient(): VoiceWsClient {
  if (client) return client
  client = new VoiceWsClient()
  wireEvents()
  return client
}

async function ensureClient(): Promise<VoiceWsClient> {
  if (client?.connected) return client

  const vs = useVoiceStore.getState()
  vs.setMicState('connecting_voice_ws')
  log('connecting_voice_ws')

  // ROOT B: before rebuilding, fully tear down any prior client. Previously this
  // branch overwrote `client`/`chatUnsub` and pushed onto a stale `cleanups`
  // array WITHOUT disconnecting the old client — leaking an auto-reconnecting
  // socket + its heartbeat interval + visibilitychange listener + duplicate
  // handlers on every reconnect gap. Flush cleanups, drop the chat sub, disconnect.
  if (client) {
    cleanups.forEach((fn) => fn())
    cleanups = []
    if (chatUnsub) { chatUnsub(); chatUnsub = null }
    client.disconnect()
    client = null
  }

  client = new VoiceWsClient()
  wireEvents()

  try {
    await client.connect()
  } catch (err) {
    // P4S-VOICE-WS-AUTH-PREFLIGHT-001: carry the PRECISE typed code from connect()
    // (token missing/timeout, upgrade failed, runtime timeout) instead of flattening
    // every failure to a generic "unavailable" that lies about the boundary. The
    // adapter renders the human string per code; here we just set the outcome + a
    // matching message and re-throw the typed error unchanged.
    const { outcome, message } = classifyVoiceWsError(err)
    log('voice_ws_failed', outcome)
    vs.setError(message)
    vs.setLastOutcome(outcome)
    vs.setMicState('idle')
    client = null
    throw err
  }

  return client
}

function releaseHeldMessage(): void {
  if (!heldVoiceMessage) return
  log('[VoiceTurn] message_released', heldVoiceMessage.id)
  const cs = useChatStore.getState()
  const existing = cs.messages.find(m => m.id === heldVoiceMessage!.id)
  if (!existing) {
    cs.pushExternalMessage({
      id: heldVoiceMessage.id,
      sender: 'assistant',
      content: heldVoiceMessage.content,
      timestamp: new Date().toISOString(),
      origin_channel: 'cockpit',
    })
  }
  heldVoiceMessage = null
  useVoiceStore.getState().setVoicePresentationStatus('idle')
}

function wireEvents(): void {
  if (!client) return

  cleanups.push(
    client.on('connected', () => {
      log('voice_ws_connected')
    })
  )

  cleanups.push(
    client.on('disconnected', () => {
      log('voice_ws_disconnected')
      useVoiceStore.getState().setMicState('idle')
      useVoiceStore.getState().setTtsState('idle')
      useVoiceStore.getState().setAudioLevel(0)
      releaseHeldMessage()
      sessionTimers.clearAll()
    })
  )

  cleanups.push(
    client.on('vad_status', (data) => {
      const active = data.active as boolean
      const voiceStore = useVoiceStore.getState()
      voiceStore.setVadActive(active)

      if (active && voiceStore.ttsState === 'speaking') {
        // Barge-in: user speaks while DEX is talking — cancel TTS.
        log('[VoiceTurn] barge_in')
        client?.cancelTts()
        cancelPlayback()
        voiceStore.setTtsState('idle')
        voiceStore.setVoicePresentationStatus('idle')
        // ROOT A: 'interrupted' must never persist over a LIVE recorder/session — if
        // one is in flight, tear it down (no dangling recorder the next tap's guard
        // would bail on). With nothing live, 'interrupted' is a transient display
        // state a fresh tap clears.
        if (recorder || (activeSession && !activeSession.done)) {
          abortActiveRecording()
        } else {
          voiceStore.setMicState('interrupted')
        }
      }
    })
  )

  // P4S-31D1-F: no `audio_level` handler — the note rail streams no live PCM, so
  // the server emits no audio_level during a note. The RMS meter is driven by the
  // controller's metering AnalyserNode (startMeterAnalyser), not server events.

  cleanups.push(
    client.on('transcript', (data) => {
      const text = data.text as string
      const isFinal = data.final as boolean
      log('transcript_received', `final=${isFinal}`)

      const vs = useVoiceStore.getState()
      vs.setLastTranscript(text)
      const vms = useVoiceMessageStore.getState()

      // P4S-31D1-F: this top-level `transcript` handler is retained for any live
      // WS transcript (e.g. a future LiveVoiceSession), but the note rail no
      // longer relies on it — the blob is transcribed via _transcribeBlob, which
      // uses its OWN scoped transcript listener. Partials are display-only and
      // NEVER enter chat/input/draft text.
      if (!isFinal) {
        updatePartial(text)
        vms.updateActivePartial(text)
        return
      }
    })
  )

  cleanups.push(
    client.on('error', (data) => {
      const code = data.code as string
      const message = data.message as string
      log('server_error', code, message)
      // ROOT F: while a transcribeUtterance round-trip is in flight, IT owns the
      // error channel (its scoped listener returns the PRECISE code, which
      // _finalizeRecording maps + stamps via markFailed). This top-level handler
      // must NOT also stamp a generic STT_FAILED — that double-write raced the
      // scoped one and clobbered the precise code (or hit the wrong draft). Let the
      // scoped listener own it; we no-op the draft-marking half here.
      if (transcribeInFlight) {
        log('server_error_deferred_to_scoped_transcribe_listener', code)
        return
      }
      const vs = useVoiceStore.getState()
      vs.setError(message || 'Voice server error')
      vs.setLastOutcome('STT_FAILED')
      vs.setMicState('idle')
      // STT failed OUTSIDE a blob transcribe (e.g. a live session) — keep draft+audio.
      const vms = useVoiceMessageStore.getState()
      if (vms.recordingState === 'transcribing' && vms.activeDraftId) {
        vms.markTranscriptFailed('STT_FAILED')
      }
      releaseHeldMessage()
      sessionTimers.clearAll()
    })
  )

  cleanups.push(
    client.on('tts_status', (data) => {
      const speaking = data.speaking as boolean
      log('tts_status', speaking ? 'speaking' : 'done')
      const vs = useVoiceStore.getState()
      if (speaking) {
        vs.setTtsState('speaking')
        releaseHeldMessage()
      } else {
        vs.setTtsState('idle')
      }
    })
  )

  cleanups.push(
    client.on('tts_error', (data) => {
      log('tts_error', data.error)
      const vs = useVoiceStore.getState()
      vs.setError(`Voice unavailable: ${data.error}`)
      vs.setTtsState('tts_failed')
      releaseHeldMessage()
      setTimeout(() => {
        useVoiceStore.getState().setTtsState('idle')
      }, 3000)
    })
  )

  let lastMsgCount = useChatStore.getState().messages.length
  chatUnsub = useChatStore.subscribe((state) => {
    const msgs = state.messages
    if (msgs.length <= lastMsgCount) {
      lastMsgCount = msgs.length
      return
    }
    lastMsgCount = msgs.length

    const voiceState = useVoiceStore.getState()
    if (!voiceState.pendingVoiceResponse) return

    const last = msgs[msgs.length - 1]
    if (last?.sender !== 'assistant') return

    log('dex_response_received', last.content?.slice(0, 60))
    sessionTimers.clear('pendingResponse')
    voiceState.setPendingVoiceResponse(false)
    voiceState.setMicState('idle')

    // Update voice route in device session store if routing metadata is present
    if (last.metadata?.routing) {
      try {
        const { useDeviceSessionStore } = require('../stores/deviceSessionStore')
        const r = last.metadata.routing as Record<string, string>
        useDeviceSessionStore.getState().setVoiceRoute({
          inputDevice: r.input_device ?? '',
          controlSurface: r.control_surface ?? '',
          executionTarget: r.execution_target ?? '',
          audioOutputDevice: r.audio_output_device ?? '',
          audioOutputSession: r.audio_output_session ?? '',
          handoffMode: r.handoff_mode ?? 'conversation',
          routeReason: r.route_reason ?? '',
        })
      } catch {
        // non-critical
      }
    }

    if (client && last.content) {
      // Hold the text message — remove from chat until TTS audio arrives.
      // Text + audio reveal together (organism response commit).
      heldVoiceMessage = { id: last.id, content: last.content }
      useChatStore.getState().removeMessage(last.id)
      log('[VoiceTurn] message_held', last.id)

      voiceState.setTtsState('generating_tts')
      voiceState.setVoicePresentationStatus('preparing_voice')

      sessionTimers.arm('ttsGenerate', () => {
        const v = useVoiceStore.getState()
        if (v.ttsState === 'generating_tts') {
          log('tts_generate_timeout')
          v.setTtsState('tts_failed')
          v.setVoicePresentationStatus('complete')
          v.setError('Voice generation timed out — showing text')
          releaseHeldMessage()
          setTimeout(() => {
            useVoiceStore.getState().setTtsState('idle')
            useVoiceStore.getState().setVoicePresentationStatus('idle')
          }, 3000)
        }
      }, TTS_GENERATE_TIMEOUT_MS)

      // Use spoken_text if available (concise TTS-friendly version)
      const ttsText = (last.metadata?.spoken_text as string | undefined) || last.content
      client.requestTts(ttsText)
    } else {
      voiceState.setVoicePresentationStatus('complete')
      setTimeout(() => useVoiceStore.getState().setVoicePresentationStatus('idle'), 500)
    }
    _pendingVoiceTurnId = null
  })
}

export async function startVoice(signal?: AbortSignal): Promise<void> {
  const vs = useVoiceStore.getState()

  // P4S-31D1-C: exactly ONE active recorder. A second mic tap while a recording
  // is LIVE must not spawn a concurrent recorder / zombie "listening…" card —
  // finalize the in-flight one first, then the caller taps again to start fresh.
  //
  // P4S31 DEADLOCK FIX: only 'listening'/'recording' mean a recording is actually
  // in flight. 'requesting_permission'/'connecting_voice_ws' are STARTUP states —
  // and on the single-gesture flow startVoice() is REACHED with micState already
  // === 'requesting_permission' (startCapture set it, then called _consentAndStart
  // → startVoice on the active-consent path). Treating those startup states as
  // "already active" made startVoice() return immediately, stranding the button
  // forever at "Requesting mic…". The real re-entrancy guard is a live recorder,
  // checked just below (recorder || finalizing).
  const activeState = vs.micState
  if (activeState === 'listening' || activeState === 'recording') {
    log('start_ignored_recorder_active', activeState)
    _finalizeRecording('manual_stop')
    return
  }
  // P3: a live recorder OR an un-finalized session means a capture is in flight.
  // `activeSession && !activeSession.done` is the finalize latch (was `finalizing`).
  if (recorder || (activeSession && !activeSession.done)) {
    log('start_ignored_recorder_or_finalizing')
    return
  }

  vs.setError(null)
  vs.setLastOutcome(null)
  vs.setChunksSent(0)
  sessionTimers.clearAll()

  log('mic_clicked')

  // ROOT D (iOS): unlock audio on the user gesture BEFORE any Audio.play(). On iOS
  // the silent-buffer unlock must COMPLETE within the gesture to grant later TTS
  // playback — firing it fire-and-forget let the gesture expire first, so TTS was
  // then blocked by the autoplay policy ("Tap to play audio"). Await it (bounded;
  // it self-resolves), early in the chain, before the ensureClient/startMic awaits.
  // P4S-VOICE-UNLOCK-HANG: unlockAudioForIOS() enables autoplay for LATER TTS
  // playback — it has NOTHING to do with recording. It was awaited here and, on iOS
  // 18.7 Safari, its internal audio.play() never settled → it hung the entire
  // voice-start chain until the 8s watchdog fired ("Voice did not start in time";
  // client diag proved ios_audio_unlock_await never returned). Run it FIRE-AND-FORGET
  // (and it's now internally bounded too) so a hung/failed unlock can never block the
  // mic. Worst case: the FIRST TTS response needs a tap-to-play, which is far better
  // than a dead mic button.
  log('ios_audio_unlock_fire_and_forget')
  void (async () => {
    try {
      const ok = await unlockAudioForIOS()
      log('ios_audio_unlock', ok ? 'success' : 'failed')
    } catch {
      log('ios_audio_unlock', 'error')
    }
  })()

  // Wire playback callbacks for TTS state management
  setPlaybackCallbacks(
    () => {
      const vs2 = useVoiceStore.getState()
      if (vs2.ttsState === 'speaking') {
        vs2.setTtsState('idle')
      }
      releaseHeldMessage()
    },
    (reason: string) => {
      log('tts_play_rejected', reason)
      const vs2 = useVoiceStore.getState()
      vs2.setTtsState('tts_failed')
      vs2.setError(`Tap to play audio (${reason})`)
      releaseHeldMessage()
    },
  )

  vs.setMicState('requesting_permission')

  // P4S-VOICE-WS-FRAMELESS-SOCKET-002: do NOT open the voice WS here. The WS is
  // REQUEST-SCOPED and only carries the buffered audio at FINALIZE — startMic() below
  // never touches the socket (it only acquires/validates the MediaStream), and
  // _transcribeBlob() opens/reuses the WS at finalize right before sending the control
  // frame. Opening it now created an ACCEPTED-but-FRAMELESS idle socket that any
  // mobile-Safari abort in the startMic/recorder window tore down in ~0.3s (server
  // logs: open→close, no frame, no handler body) — the live failure the user saw.
  // We still need a client instance for startMic()'s stream bookkeeping; get one
  // WITHOUT connecting the socket.
  const c = getOrCreateClient()

  log('start_mic_await')

  let stream: MediaStream
  let captureDiagnostics: Record<string, unknown> = {}
  try {
    const started = await c.startMic()
    stream = started.stream
    captureDiagnostics = started.diagnostics
    log('mic_stream_live', `trackState=${started.trackState}`)
    // P4S-31D1-F: startMic now returns the RAW validated stream (no capture
    // AudioContext). If the track is not live, capture will be silent — surface
    // it immediately rather than after a dead recording.
    if (captureDiagnostics.track_ready_state !== 'live') {
      log('capture_track_not_live', String(captureDiagnostics.track_ready_state))
    }
  } catch (err: unknown) {
    const error = err as Error & { name?: string }
    log('mic_failed', error.name, error.message)

    if (error.name === 'NotAllowedError') {
      vs.setError('Microphone permission denied — check browser settings')
      vs.setLastOutcome('MIC_PERMISSION_DENIED')
    } else if (error.name === 'NotFoundError') {
      vs.setError('No microphone found')
      vs.setLastOutcome('MIC_DEVICE_UNAVAILABLE')
    } else if (error.name === 'NotSupportedError') {
      vs.setError('Browser does not support microphone capture')
      vs.setLastOutcome('MIC_DEVICE_UNAVAILABLE')
    } else {
      vs.setError(`Mic error: ${error.message || 'unknown'}`)
      vs.setLastOutcome('MIC_DEVICE_UNAVAILABLE')
    }

    vs.setMicState('idle')
    return
  }

  // P4: the watchdog may have aborted the chain while startMic awaited. The mic is
  // now open but the session was torn down — release it instead of resurrecting a
  // live recorder over a dead/abandoned session.
  if (signal?.aborted) {
    log('start_aborted_after_start_mic')
    teardownCapture()
    return
  }

  // Fresh recording-session accumulators (blob-only: no VAD/live-transcript state).
  recordingStartedAt = Date.now()

  // Voice turn id threads capture → transcript → chat → loop.
  const turn = createTurn()
  log('[VoiceTurn] turn_started_on_capture')

  // Create the reviewable draft in the message store (recording state). The
  // consent grant id (vcg-…) was stamped into the store by the adapter when
  // consent confirmed active; createDraft reads it as consent_grant_id.
  let deviceRegistryId = 'desktop_browser'
  let sessionId = ''
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useDeviceSessionStore } = require('../stores/deviceSessionStore')
    const routing = useDeviceSessionStore.getState().getRoutingMetadata() as Record<string, string>
    deviceRegistryId = routing.source_device_id || deviceRegistryId
    sessionId = routing.source_session_id || ''
  } catch {
    // device session store unavailable — role-based id + empty session
  }

  const draft = useVoiceMessageStore.getState().createDraft({
    voiceTurnId: turn.voiceTurnId,
    deviceRegistryId,
    sessionId,
  })

  // P3: bind the whole capture to ONE session object. draftId is captured HERE and
  // used by every completion handler — a later delete/new-recording can rebind the
  // store's activeDraftId without corrupting this capture's outcome. `done` is the
  // finalize latch (replaces the bare `finalizing` flag).
  activeSession = {
    id: `vcs-${++_sessionSeq}-${recordingStartedAt}`,
    draftId: draft.draft_id,
    turnId: turn.voiceTurnId,
    done: false,
  }

  // BLOB-ONLY capture: MediaRecorder on the raw stream is the sole artifact.
  _startRecorder(stream)
  // P4S-VOICE-CLIENT-DIAG: recording started — flush the SUCCESS timeline so we can
  // compare a working tap's stage timings against a failing one.
  log('recorder_started')
  diagFlush('recording_started')

  // Metering AnalyserNode on the SAME stream feeds client.clientRms; the ~10Hz
  // store poll mirrors it into the recording card so the bar visibly moves.
  startMeterAnalyser(stream)
  startCaptureMeter()

  vs.setMicState('listening')
  log('state=listening', 'tap mic again to send')

  sessionTimers.arm('maxRecording', () => {
    log('max_recording_timeout', `${VAD_CONFIG.max_recording_ms}ms`)
    const v = useVoiceStore.getState()
    if (v.micState === 'listening' || v.micState === 'recording') {
      v.setError('Recording stopped — duration limit reached')
      _finalizeRecording('silence_timeout')
    }
  }, VAD_CONFIG.max_recording_ms)
}

/**
 * Stop the current recording. Manual tap-to-stop finalizes the draft to review
 * (NOT a chat message). Idempotent when nothing is recording.
 */
export function stopVoice(): void {
  log('stop_voice')
  const vs = useVoiceStore.getState()
  const currentState = vs.micState

  if (currentState === 'listening' || currentState === 'recording') {
    _finalizeRecording('manual_stop')
    return
  }

  cancelTurn()
  teardownCapture()
  vs.setMicState('idle')
  vs.setAudioLevel(0)
  vs.setVadActive(false)
}

/**
 * Abort the active recording with no dispatch and no chat trace (delete of an
 * in-flight draft). Mic + recorder down; the store owns draft removal.
 */
export function abortActiveRecording(): void {
  log('abort_active_recording')
  // P3: end the session cleanly. `done = true` blocks any in-flight finalize from
  // double-running; then we DROP the session (null) so the next startVoice's guard
  // (`activeSession && !activeSession.done`) passes and the mic works again. This
  // replaces the fragile manual `finalizing = true; …; finalizing = false` dance
  // (the "after I deleted it, voice wouldn't work again" field bug).
  if (activeSession) activeSession.done = true
  cancelTurn()
  teardownCapture()
  const vs = useVoiceStore.getState()
  vs.setMicState('idle')
  vs.setAudioLevel(0)
  vs.setVadActive(false)
  activeSession = null
  recorder = null
}

/**
 * Arm the TTS/held-message presentation for a sent voice message. Moved here
 * from the old auto-dispatch: the chat message already exists (sendDraft pushed
 * it); this only primes the response-hold path so the assistant reply reveals
 * text+audio together.
 */
export function notifyVoiceMessageSent(voiceTurnId: string): void {
  _pendingVoiceTurnId = voiceTurnId
  const vs = useVoiceStore.getState()
  vs.setMicState('processing')
  vs.setPendingVoiceResponse(true)
  vs.setVoicePresentationStatus('thinking')
  vs.setError(null)
  vs.setLastOutcome('TRANSCRIPT_RECEIVED')
  log('[VoiceTurn] voice_message_sent', voiceTurnId)

  sessionTimers.arm('pendingResponse', () => {
    const v = useVoiceStore.getState()
    if (v.pendingVoiceResponse) {
      v.setPendingVoiceResponse(false)
      v.setMicState('idle')
      v.setVoicePresentationStatus('idle')
      v.setError('Response timed out — try again')
      v.setLastOutcome('TIMEOUT')
      releaseHeldMessage()
      _pendingVoiceTurnId = null
      log('response_timeout')
    }
  }, PENDING_RESPONSE_TIMEOUT_MS)
}

// ── Lane E: STT retry against the preserved audio blob ───────────────────────
// P4S31 DURABLE: client-side decode (_resampleToPcm16 via AudioContext) was
// REMOVED — it's fragile (iOS Safari can't decode its own MediaRecorder mp4) and
// unnecessary. All decoding is server-side ffmpeg now (see _transcribeBlob).

/**
 * Outcome of transcribing a blob over the WS-STT path. Distinct from the store
 * mutations so the SAME decode/stream machinery drives both the finalize
 * fallback (activeDraft actions) and the retry (per-draftId actions) without
 * either caller reimplementing the WS transport (codebase quality: one helper).
 */
type BlobTranscribeResult =
  | { ok: true; text: string; confidence: number | null }
  | { ok: false; code: VoiceArtifactErrorCode | 'WS_UNAVAILABLE' | 'DECODE_FAILED' | 'TIMEOUT' }

/**
 * Binding pre-flight for blob-sourced transcription. The locally-captured blob
 * is the source of truth — before we stream it we assert it is a real,
 * decodable artifact bound to THIS draft. Returns a precise
 * VoiceArtifactErrorCode on violation, or null when the blob is sound.
 * NEVER returns a "no audio" verdict while a size>0 blob is present.
 */
function _assertTranscribableBlob(
  draftId: string,
  blob: Blob | null,
): VoiceArtifactErrorCode | null {
  if (!draftId) return VOICE_ARTIFACT_ERROR.AUDIO_ARTIFACT_REF_NOT_FOUND
  if (!blob) return VOICE_ARTIFACT_ERROR.MISSING_AUDIO_FIELD
  if (blob.size <= 0) return VOICE_ARTIFACT_ERROR.EMPTY_AUDIO_BLOB
  // mimeType must be present AND an audio container we can decode.
  const mime = (blob.type || '').split(';')[0].trim().toLowerCase()
  if (!mime || !mime.startsWith('audio/')) {
    return VOICE_ARTIFACT_ERROR.UNSUPPORTED_AUDIO_FORMAT
  }
  return null
}

/**
 * SINGLE shared decode→stream→collect helper (P4S-31D1-E). Decodes the blob to
 * 16kHz PCM16 and streams it once over the ONE governed voice WS using the GAP F
 * protocol (control frame → PCM chunks → terminator, in transcribeUtterance),
 * resolving with the first final transcript. Used by BOTH the finalize fallback
 * and the Lane E retry — the decode/stream logic lives here ONCE.
 */
async function _transcribeBlob(draftId: string, blob: Blob): Promise<BlobTranscribeResult> {
  // Binding assertions: real artifact, non-empty, decodable mime, bound to draft.
  const bindErr = _assertTranscribableBlob(draftId, blob)
  if (bindErr) {
    log('transcribe_blob_binding_failed', draftId, bindErr)
    return { ok: false, code: bindErr }
  }

  let c: VoiceWsClient
  try {
    c = await ensureClient()
  } catch {
    return { ok: false, code: 'WS_UNAVAILABLE' }
  }

  const consent = await voiceConsentForCapture()
  if (!consent.consentGrantId) {
    return { ok: false, code: 'CONSENT_DENIED' }
  }

  // P4S31 DURABLE: SERVER-DECODE PRIMARY — the way Apple / WhatsApp / Telegram /
  // Instagram do it. Never client-decode the recording (AudioContext.decodeAudioData
  // can't decode iOS Safari's OWN MediaRecorder mp4 — a WebKit round-trip bug — and
  // it's fragile everywhere). Send the RAW container blob with its real content_type
  // and let the server's robust ffmpeg (normalize_to_pcm_wav, CPU-gated) decode it.
  // One path for every surface — no browser-specific decode divergence.
  const contentType = blob.type || 'audio/mp4'
  const raw = await blob.arrayBuffer()
  if (raw.byteLength === 0) {
    return { ok: false, code: VOICE_ARTIFACT_ERROR.EMPTY_AUDIO_BLOB }
  }
  log('transcribe_blob_server_decode', draftId, contentType, `${raw.byteLength}B`)
  const res = await c.transcribeUtterance(
    [raw],
    {
      source: consent.source,
      deviceRegistryId: consent.deviceRegistryId,
      consentGrantId: consent.consentGrantId,
      activationMode: 'push_to_talk',
      contentType,
    },
    // Server ffmpeg-decode + whisper takes longer than raw PCM — give it room.
    25_000,
  )
  if (res.ok) return { ok: true, text: res.text, confidence: null }
  return { ok: false, code: res.code }
}

/**
 * Lane E. Re-run STT over a failed draft's stored audio via the SHARED
 * `_transcribeBlob` helper (no duplicated decode/stream logic). On success:
 * completeRetry. On failure: markRetryFailed with a precise code — audio kept.
 */
export async function retryDraftTranscription(draftId: string): Promise<void> {
  const vms = useVoiceMessageStore.getState()
  const draft = vms.drafts.find((d) => d.draft_id === draftId)
  if (!draft) return
  // Binding: a present, non-empty blob is required — never "no audio" if it exists.
  const bindErr = _assertTranscribableBlob(draftId, draft.audioBlob)
  if (bindErr) {
    vms.markRetryFailed(draftId, bindErr)
    return
  }

  vms.beginRetry(draftId)

  const res = await _transcribeBlob(draftId, draft.audioBlob as Blob)
  if (res.ok) {
    // P4S31: STT is local faster-whisper now (no Groq). Label reflects the truth.
    useVoiceMessageStore.getState().completeRetry(draftId, res.text, 'faster_whisper')
    return
  }
  // Map transport-level outcomes to the retry taxonomy the UI already renders.
  const RETRY_CODE: Record<string, string> = {
    WS_UNAVAILABLE: 'RETRY_WS_UNAVAILABLE',
    DECODE_FAILED: 'RETRY_DECODE_FAILED',
    STT_FAILED: 'RETRY_STT_FAILED',
    TIMEOUT: 'RETRY_TIMEOUT',
    LOCAL_AUDIO_PRESENT_UPLOAD_MISSING: VOICE_ARTIFACT_ERROR.LOCAL_AUDIO_PRESENT_UPLOAD_MISSING,
    LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY: VOICE_ARTIFACT_ERROR.LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY,
  }
  useVoiceMessageStore.getState().markRetryFailed(draftId, RETRY_CODE[res.code] ?? res.code)
}

export function speakResponse(text: string): void {
  if (!client) return
  client.requestTts(text)
}

export function stopTts(): void {
  if (client) {
    client.cancelTts()
  }
  cancelPlayback()
  useVoiceStore.getState().setTtsState('idle')
  releaseHeldMessage()
}

export function destroyVoice(): void {
  cancelTurn()
  teardownCapture()
  if (activeSession) activeSession.done = true
  activeSession = null
  recorder = null
  transcribeInFlight = false
  cleanups.forEach(fn => fn())
  cleanups = []
  if (chatUnsub) {
    chatUnsub()
    chatUnsub = null
  }
  releaseHeldMessage()
  resetPlayback()
  _pendingVoiceTurnId = null
  void getCurrentTurn
  if (client) {
    client.disconnect()
    client = null
  }
}
