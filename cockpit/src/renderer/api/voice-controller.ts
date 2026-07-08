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
import { VoiceWsClient } from './voice-ws'
import { useVoiceStore } from '../stores/voiceStore'
import { useChatStore } from '../stores/chatStore'
import { useVoiceMessageStore, VAD_CONFIG } from '../stores/voiceMessageStore'
import { unlockAudioForIOS, setPlaybackCallbacks, cancelPlayback, resetPlayback } from './tts-playback-controller'
import { createTurn, updatePartial, cancelTurn, getCurrentTurn } from './voice-turn-assembler'

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
export const VOICE_ARTIFACT_ERROR = {
  /** Blob exists (size>0) but nothing was streamed to the STT WS. */
  LOCAL_AUDIO_PRESENT_UPLOAD_MISSING: 'LOCAL_AUDIO_PRESENT_UPLOAD_MISSING',
  /** PCM was streamed but the server saw 0 bytes / no audio energy. */
  LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY: 'LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY',
  /** The referenced audio artifact could not be located for transcription. */
  AUDIO_ARTIFACT_REF_NOT_FOUND: 'AUDIO_ARTIFACT_REF_NOT_FOUND',
  /** The draft carried no audio field at all (blob null). */
  MISSING_AUDIO_FIELD: 'MISSING_AUDIO_FIELD',
  /** The audio blob is present but zero-length. */
  EMPTY_AUDIO_BLOB: 'EMPTY_AUDIO_BLOB',
  /** The blob mime type is absent or not a decodable audio container. */
  UNSUPPORTED_AUDIO_FORMAT: 'UNSUPPORTED_AUDIO_FORMAT',
  /** WebAudio could not decode the blob to PCM. */
  DECODE_FAILED: 'DECODE_FAILED',
  /** The STT WS path failed / timed out after valid PCM was sent. */
  STT_FAILED: 'STT_FAILED',
} as const

export type VoiceArtifactErrorCode = keyof typeof VOICE_ARTIFACT_ERROR

let client: VoiceWsClient | null = null
let cleanups: (() => void)[] = []
let chatUnsub: (() => void) | null = null
let pendingTimeout: ReturnType<typeof setTimeout> | null = null
let maxRecordingTimeout: ReturnType<typeof setTimeout> | null = null
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
let finalizing = false
let onRecorderStop: ((blob: Blob | null) => void) | null = null

// Metering AnalyserNode (meter-ONLY: RMS bar + silent-mic hint). No VAD, no
// finalize — it can never re-introduce the two-path divergence bug class.
let meterAudioContext: AudioContext | null = null
let meterAnalyser: AnalyserNode | null = null
let meterSource: MediaStreamAudioSourceNode | null = null
let meterRafId: number | null = null

const PENDING_RESPONSE_TIMEOUT_MS = 30_000
const TTS_GENERATE_TIMEOUT_MS = 15_000
/** Meter poll cadence — ~10Hz is enough to look live and stays cheap. */
const METER_POLL_MS = 100
/** Peak RMS below this after MIC_SILENT_HINT_MS means the mic looks silent. */
const MIC_SILENT_RMS_FLOOR = 0.005
/** How long capture may stay flat-at-0 before we surface the silent-mic hint. */
const MIC_SILENT_HINT_MS = 2_000

const log = (stage: string, ...args: unknown[]) =>
  console.log(`[VoicePipeline] ${stage}`, ...args)

function clearAllTimers(): void {
  if (pendingTimeout) { clearTimeout(pendingTimeout); pendingTimeout = null }
  if (maxRecordingTimeout) { clearTimeout(maxRecordingTimeout); maxRecordingTimeout = null }
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
    // silentMs: elapsed only counts toward the hint once we're past the grace
    // window AND the session has never risen above the silence floor.
    const peak = useVoiceMessageStore.getState().captureRmsPeak
    const silentMs =
      elapsed >= MIC_SILENT_HINT_MS && Math.max(peak, rms) < MIC_SILENT_RMS_FLOOR
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
  if (typeof MediaRecorder === 'undefined') {
    log('media_recorder_unavailable')
    recorder = null
    return
  }
  try {
    const mime = _pickRecorderMime()
    recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream)
    recorder.ondataavailable = (e: BlobEvent) => {
      if (e.data && e.data.size > 0) recorderChunks.push(e.data)
    }
    recorder.onstop = () => {
      const type = recorder?.mimeType || recorderChunks[0]?.type || 'audio/webm'
      const blob = recorderChunks.length > 0 ? new Blob(recorderChunks, { type }) : null
      const cb = onRecorderStop
      onRecorderStop = null
      if (cb) cb(blob)
    }
    recorder.start()
    log('recorder_started', recorder.mimeType)
  } catch (e) {
    log('recorder_start_failed', e)
    recorder = null
  }
}

/** Stop the recorder and deliver the assembled blob to `cb` (null if none). */
function _stopRecorder(cb: (blob: Blob | null) => void): void {
  if (recorder && recorder.state !== 'inactive') {
    onRecorderStop = cb
    try {
      recorder.stop()
    } catch {
      onRecorderStop = null
      cb(null)
    }
  } else {
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
  if (finalizing) return
  finalizing = true
  clearAllTimers()
  stopCaptureMeter()
  stopMeterAnalyser()

  const now = Date.now()
  const durationMs = recordingStartedAt ? now - recordingStartedAt : 0

  // BLOB-ONLY: the captured blob is the single source of truth. Mark the draft
  // finalizing/transcribing up front; the real "no speech" authority is the
  // server (SILENT_AUDIO / VAD_NO_SPEECH via _transcribeBlob), not a client
  // silence estimate. The draft it binds to is fixed now, before
  // completeActiveTranscript clears activeDraftId.
  useVoiceMessageStore.getState().finalizeActiveDraft(finalizedBy, durationMs, null, now)
  useVoiceStore.getState().setMicState('transcribing')
  const finalizingDraftId = useVoiceMessageStore.getState().activeDraftId

  if (client) client.stopMic()

  // Stop the recorder, then decide from the BLOB (its size only known here).
  _stopRecorder((blob) => {
    if (blob) useVoiceMessageStore.getState().attachAudio(blob)
    const draftId = finalizingDraftId

    // No usable blob → recoverable missing/empty draft, NEVER a chat message.
    // Precise artifact code (blob-size based, not a client speech estimate).
    if (!blob || blob.size <= 0) {
      if (draftId) {
        const code = !blob
          ? VOICE_ARTIFACT_ERROR.MISSING_AUDIO_FIELD
          : VOICE_ARTIFACT_ERROR.EMPTY_AUDIO_BLOB
        useVoiceMessageStore.getState().markTranscriptFailed(code)
      } else {
        useVoiceMessageStore.getState().markNoSpeech()
      }
      useVoiceStore.getState().setMicState('idle')
      log('recording_no_usable_blob', `duration=${durationMs}`)
      return
    }

    // BLOB SOURCE-OF-TRUTH (the only transcription path): transcribe FROM the
    // captured blob using the SAME shared machinery retry uses. _transcribeBlob
    // → _assertTranscribableBlob + server VAD are the real empty/no-speech
    // authority. NEVER report "no audio" here while a size>0 blob exists.
    if (draftId) {
      void _transcribeBlob(draftId, blob).then((res) => {
        if (res.ok) {
          useVoiceMessageStore.getState().completeActiveTranscript(res.text, res.confidence)
          useVoiceStore.getState().setMicState('idle')
          return
        }
        // Precise failure — audio is preserved, draft stays retryable.
        const FINALIZE_CODE: Record<string, string> = {
          WS_UNAVAILABLE: 'STT_FAILED',
          DECODE_FAILED: VOICE_ARTIFACT_ERROR.DECODE_FAILED,
          STT_FAILED: VOICE_ARTIFACT_ERROR.STT_FAILED,
          TIMEOUT: 'STT_FAILED',
          LOCAL_AUDIO_PRESENT_UPLOAD_MISSING: VOICE_ARTIFACT_ERROR.LOCAL_AUDIO_PRESENT_UPLOAD_MISSING,
          LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY: VOICE_ARTIFACT_ERROR.LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY,
        }
        useVoiceMessageStore.getState().markTranscriptFailed(FINALIZE_CODE[res.code] ?? res.code)
        useVoiceStore.getState().setMicState('idle')
      })
    }
  })
  log('recording_finalized', finalizedBy, `duration=${durationMs}`)
}

async function ensureClient(): Promise<VoiceWsClient> {
  if (client?.connected) return client

  const vs = useVoiceStore.getState()
  vs.setMicState('connecting_voice_ws')
  log('connecting_voice_ws')

  client = new VoiceWsClient()
  wireEvents()

  try {
    await client.connect()
  } catch (err) {
    log('voice_ws_unavailable', err)
    vs.setError('Voice server unavailable — check connection')
    vs.setLastOutcome('VOICE_WS_UNAVAILABLE')
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
      clearAllTimers()
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
        voiceStore.setMicState('interrupted')
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
      const vs = useVoiceStore.getState()
      vs.setError(message || 'Voice server error')
      vs.setLastOutcome('STT_FAILED')
      vs.setMicState('idle')
      // STT failed after finalize: keep the draft + audio, mark recoverable.
      const vms = useVoiceMessageStore.getState()
      if (vms.recordingState === 'transcribing' && vms.activeDraftId) {
        vms.markTranscriptFailed('STT_FAILED')
      }
      releaseHeldMessage()
      clearAllTimers()
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
    if (pendingTimeout) { clearTimeout(pendingTimeout); pendingTimeout = null }
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

      const ttsTimeout = setTimeout(() => {
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

      cleanups.push(() => clearTimeout(ttsTimeout))
    } else {
      voiceState.setVoicePresentationStatus('complete')
      setTimeout(() => useVoiceStore.getState().setVoicePresentationStatus('idle'), 500)
    }
    _pendingVoiceTurnId = null
  })
}

export async function startVoice(): Promise<void> {
  const vs = useVoiceStore.getState()

  // P4S-31D1-C: exactly ONE active recorder. A second mic tap while a recording
  // is live must not spawn a concurrent recorder / zombie "listening…" card —
  // finalize the in-flight one first, then the caller taps again to start fresh.
  const activeState = vs.micState
  if (
    activeState === 'listening' ||
    activeState === 'recording' ||
    activeState === 'requesting_permission' ||
    activeState === 'connecting_voice_ws'
  ) {
    log('start_ignored_recorder_active', activeState)
    if (activeState === 'listening' || activeState === 'recording') {
      _finalizeRecording('manual_stop')
    }
    return
  }
  if (recorder || finalizing) {
    log('start_ignored_recorder_or_finalizing')
    return
  }

  vs.setError(null)
  vs.setLastOutcome(null)
  vs.setChunksSent(0)
  clearAllTimers()

  log('mic_clicked')

  // Unlock audio on user gesture (iOS requires this before any Audio.play())
  unlockAudioForIOS().then((ok) => {
    log('ios_audio_unlock', ok ? 'success' : 'failed')
  }).catch(() => {
    log('ios_audio_unlock', 'error')
  })

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

  let c: VoiceWsClient
  try {
    c = await ensureClient()
  } catch {
    return
  }

  log('permission_requesting')

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

  // Fresh recording-session accumulators (blob-only: no VAD/live-transcript state).
  recordingStartedAt = Date.now()
  finalizing = false

  // Voice turn id threads capture → transcript → chat → loop.
  const turn = createTurn()
  log('[VoiceTurn] turn_started_on_mic_start')

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

  useVoiceMessageStore.getState().createDraft({
    voiceTurnId: turn.voiceTurnId,
    deviceRegistryId,
    sessionId,
  })

  // BLOB-ONLY capture: MediaRecorder on the raw stream is the sole artifact.
  _startRecorder(stream)

  // Metering AnalyserNode on the SAME stream feeds client.clientRms; the ~10Hz
  // store poll mirrors it into the recording card so the bar visibly moves.
  startMeterAnalyser(stream)
  startCaptureMeter()

  vs.setMicState('listening')
  log('state=listening', 'tap mic again to send')

  maxRecordingTimeout = setTimeout(() => {
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

  if (client) client.stopMic()
  cancelTurn()
  clearAllTimers()
  stopCaptureMeter()
  stopMeterAnalyser()
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
  clearAllTimers()
  stopCaptureMeter()
  stopMeterAnalyser()
  finalizing = true
  if (client) client.stopMic()
  _stopRecorder(() => { /* discard — deleteDraft revokes any attached blob */ })
  cancelTurn()
  const vs = useVoiceStore.getState()
  vs.setMicState('idle')
  vs.setAudioLevel(0)
  vs.setVadActive(false)
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

  pendingTimeout = setTimeout(() => {
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

/** Decode → 16kHz mono PCM16 → stream over the voice WS → collect final. */
async function _resampleToPcm16(blob: Blob): Promise<Int16Array[]> {
  const AudioCtx = (window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext)
  if (!AudioCtx) throw new Error('AUDIO_DECODE_UNAVAILABLE')
  const arrayBuf = await blob.arrayBuffer()
  const decodeCtx = new AudioCtx()
  let decoded: AudioBuffer
  try {
    decoded = await decodeCtx.decodeAudioData(arrayBuf)
  } finally {
    if (decodeCtx.state !== 'closed') decodeCtx.close()
  }

  const targetRate = 16000
  const src = decoded.getChannelData(0)
  const ratio = decoded.sampleRate / targetRate
  const outLen = Math.floor(src.length / ratio)
  const mono = new Float32Array(outLen)
  for (let i = 0; i < outLen; i++) {
    // Nearest-neighbour downsample; adequate for whisper-class STT.
    mono[i] = src[Math.floor(i * ratio)]
  }

  const chunkSize = 4096
  const chunks: Int16Array[] = []
  for (let off = 0; off < mono.length; off += chunkSize) {
    const slice = mono.subarray(off, Math.min(off + chunkSize, mono.length))
    const pcm16 = new Int16Array(slice.length)
    for (let i = 0; i < slice.length; i++) {
      const s = Math.max(-1, Math.min(1, slice[i]))
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    chunks.push(pcm16)
  }
  return chunks
}

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
 * 16kHz PCM16, streams it over the existing voice WS (mic_start / pcm* /
 * mic_stop — the same frames the live capture uses so it carries the same
 * draft_id turn), and resolves with the first final transcript. Used by BOTH
 * the finalize fallback and the Lane E retry — the decode/stream logic lives
 * here ONCE, never duplicated across the two callers.
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

  let chunks: Int16Array[]
  try {
    chunks = await _resampleToPcm16(blob)
  } catch (e) {
    log('transcribe_blob_decode_failed', draftId, e)
    return { ok: false, code: 'DECODE_FAILED' }
  }

  // Nothing decoded to PCM — the blob had no audio energy the server can use.
  if (chunks.length === 0 || chunks.every((ch) => ch.length === 0)) {
    return { ok: false, code: VOICE_ARTIFACT_ERROR.LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY }
  }

  let settled = false
  const result = await new Promise<BlobTranscribeResult>((resolve) => {
    const offTranscript = c.on('transcript', (data) => {
      const text = data.text as string
      const isFinal = data.final as boolean
      const confidence = typeof data.confidence === 'number' ? (data.confidence as number) : null
      if (!isFinal) {
        if (text?.trim()) useVoiceMessageStore.getState().updateRetryPartial(draftId, text)
        return
      }
      if (!text.trim()) return
      if (settled) return
      settled = true
      offTranscript()
      offError()
      resolve({ ok: true, text, confidence })
    })
    const offError = c.on('error', () => {
      if (settled) return
      settled = true
      offTranscript()
      offError()
      resolve({ ok: false, code: 'STT_FAILED' })
    })
    // Bounded wait so a silent server never leaves the draft stuck transcribing.
    setTimeout(() => {
      if (settled) return
      settled = true
      offTranscript()
      offError()
      resolve({ ok: false, code: 'TIMEOUT' })
    }, 15_000)

    try {
      c.sendControl('mic_start')
      for (const chunk of chunks) c.sendPcm(chunk.buffer)
      c.sendControl('mic_stop')
    } catch {
      if (settled) return
      settled = true
      offTranscript()
      offError()
      // Streamed nothing: a present blob whose PCM never reached the server.
      resolve({ ok: false, code: VOICE_ARTIFACT_ERROR.LOCAL_AUDIO_PRESENT_UPLOAD_MISSING })
    }
  })
  return result
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
    useVoiceMessageStore.getState().completeRetry(draftId, res.text, 'groq_whisper')
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
  clearAllTimers()
  stopCaptureMeter()
  stopMeterAnalyser()
  cancelTurn()
  _stopRecorder(() => { /* discard */ })
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
