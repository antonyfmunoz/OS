import { VoiceWsClient } from './voice-ws'
import { useVoiceStore } from '../stores/voiceStore'
import { useChatStore } from '../stores/chatStore'
import { unlockAudioForIOS, setPlaybackCallbacks, cancelPlayback, resetPlayback } from './tts-playback-controller'
import {
  createTurn,
  appendSegment,
  updatePartial,
  commitTurn,
  cancelTurn,
  getCurrentTurn,
  hasTurnActive,
  startSilenceTimer,
} from './voice-turn-assembler'
import type { VoiceTurnState } from './voice-turn-assembler'

let client: VoiceWsClient | null = null
let cleanups: (() => void)[] = []
let chatUnsub: (() => void) | null = null
let pendingTimeout: ReturnType<typeof setTimeout> | null = null
let noSpeechTimeout: ReturnType<typeof setTimeout> | null = null
let maxRecordingTimeout: ReturnType<typeof setTimeout> | null = null
let heldVoiceMessage: { id: string; content: string } | null = null
/** The voice turn ID for the currently pending voice response. */
let _pendingVoiceTurnId: string | null = null

const PENDING_RESPONSE_TIMEOUT_MS = 30_000
const NO_TRANSCRIPT_TIMEOUT_MS = 10_000
const MAX_RECORDING_MS = 30_000
const TTS_GENERATE_TIMEOUT_MS = 15_000

const log = (stage: string, ...args: unknown[]) =>
  console.log(`[VoicePipeline] ${stage}`, ...args)

function clearAllTimers(): void {
  if (pendingTimeout) { clearTimeout(pendingTimeout); pendingTimeout = null }
  if (noSpeechTimeout) { clearTimeout(noSpeechTimeout); noSpeechTimeout = null }
  if (maxRecordingTimeout) { clearTimeout(maxRecordingTimeout); maxRecordingTimeout = null }
}

/**
 * Dispatch a committed voice turn as a single message to the advisor.
 * Clears the draft bubble and sets up response timeout.
 */
function _dispatchCommittedTurn(turn: VoiceTurnState): void {
  const text = turn.assembledText
  if (!text) {
    log('[VoiceTurn] dispatch_empty_turn')
    useChatStore.getState().setDraftMessage(null)
    useVoiceStore.getState().setMicState('idle')
    return
  }

  log('[VoiceTurn] dispatching', turn.voiceTurnId, text.slice(0, 80))
  _pendingVoiceTurnId = turn.voiceTurnId

  // Clear draft and show final operator message via normal chat flow
  useChatStore.getState().setDraftMessage(null)

  const vs = useVoiceStore.getState()
  vs.setMicState('processing')
  vs.setPendingVoiceResponse(true)
  vs.setVoicePresentationStatus('thinking')
  vs.setError(null)
  vs.setLastOutcome('TRANSCRIPT_RECEIVED')

  useChatStore.getState().addVoiceTranscript(text, turn.voiceTurnId)
  log('[VoiceTurn] transcript_dispatched', turn.voiceTurnId)

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
        // Barge-in: user speaks while DEX is talking — cancel TTS, start new turn
        log('[VoiceTurn] barge_in')
        client?.cancelTts()
        cancelPlayback()
        voiceStore.setTtsState('idle')
        voiceStore.setVoicePresentationStatus('idle')
        voiceStore.setMicState('interrupted')
        // Create a fresh turn for the barge-in speech
        createTurn()
        setTimeout(() => useVoiceStore.getState().setMicState('recording'), 200)
      }
    })
  )

  cleanups.push(
    client.on('audio_level', (data) => {
      const level = data.level as number
      useVoiceStore.getState().setAudioLevel(level)
      if (level > 0.02) {
        const vs = useVoiceStore.getState()
        if (vs.micState === 'listening') {
          vs.setMicState('recording')
          log('speech_detected', `level=${level}`)
        }
      }
    })
  )

  cleanups.push(
    client.on('transcript', (data) => {
      const text = data.text as string
      const isFinal = data.final as boolean
      log('transcript_received', `final=${isFinal}`, text?.slice(0, 80))

      const vs = useVoiceStore.getState()
      vs.setLastTranscript(text)

      if (!isFinal) {
        // Live partial — update draft bubble
        updatePartial(text)
        if (hasTurnActive()) {
          const turn = getCurrentTurn()
          const draftText = turn
            ? [...turn.finalSegments.map(s => s.text), text].join(' ')
            : text
          useChatStore.getState().setDraftMessage({
            id: `draft-voice-${Date.now()}`,
            sender: 'operator',
            content: draftText,
            timestamp: new Date().toISOString(),
            source: 'voice',
          })
        }
        return
      }

      // Final transcript segment
      if (!text.trim()) {
        // Empty final — only end turn if no segments collected
        if (noSpeechTimeout) { clearTimeout(noSpeechTimeout); noSpeechTimeout = null }
        const turn = getCurrentTurn()
        if (!turn || turn.finalSegments.length === 0) {
          log('no_speech_in_transcript')
          vs.setError('No speech detected — try again')
          vs.setLastOutcome('NO_SPEECH_DETECTED')
          vs.setMicState('idle')
          useChatStore.getState().setDraftMessage(null)
          cancelTurn()
        }
        return
      }

      // Append segment to current turn (don't dispatch yet)
      appendSegment(text)

      // Update draft bubble with all segments so far
      const turn = getCurrentTurn()
      if (turn) {
        useChatStore.getState().setDraftMessage({
          id: `draft-voice-${turn.voiceTurnId}`,
          sender: 'operator',
          content: turn.finalSegments.map(s => s.text).join(' '),
          timestamp: new Date().toISOString(),
          source: 'voice',
        })
      }

      // If mic already stopped (tap-to-stop), commit immediately — no more
      // segments will arrive. Otherwise wait for silence grace window.
      if (vs.micState === 'transcribing') {
        if (noSpeechTimeout) { clearTimeout(noSpeechTimeout); noSpeechTimeout = null }
        const committed = commitTurn()
        if (committed && committed.assembledText) {
          log('[VoiceTurn] post_stop_commit', committed.voiceTurnId)
          _dispatchCommittedTurn(committed)
        }
      } else {
        startSilenceTimer((committed) => {
          _dispatchCommittedTurn(committed)
        })
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
      // Playback done — release held message and reset TTS state
      const vs2 = useVoiceStore.getState()
      if (vs2.ttsState === 'speaking') {
        vs2.setTtsState('idle')
      }
      releaseHeldMessage()
    },
    (reason: string) => {
      // Playback rejected (iOS autoplay block) — show tap-to-play
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

  try {
    const { trackState } = await c.startMic()
    log('mic_stream_live', `trackState=${trackState}`)
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

  // Create a new voice turn for this recording session
  createTurn()
  log('[VoiceTurn] turn_started_on_mic_start')

  vs.setMicState('listening')
  log('state=listening', 'tap mic again to send')

  maxRecordingTimeout = setTimeout(() => {
    log('max_recording_timeout', `${MAX_RECORDING_MS}ms`)
    const v = useVoiceStore.getState()
    if (v.micState === 'listening' || v.micState === 'recording') {
      v.setError('Recording stopped — 30 second limit reached')
      finalizeMic()
    }
  }, MAX_RECORDING_MS)
}

function finalizeMic(): void {
  if (!client) return
  log('mic_finalizing', `chunks=${client.chunksSent}`)

  const vs = useVoiceStore.getState()
  vs.setMicState('transcribing')

  client.stopMic()

  if (maxRecordingTimeout) { clearTimeout(maxRecordingTimeout); maxRecordingTimeout = null }

  noSpeechTimeout = setTimeout(() => {
    const v = useVoiceStore.getState()
    if (v.micState === 'transcribing') {
      log('no_transcript_timeout')
      v.setError('No speech detected — try again')
      v.setLastOutcome('NO_SPEECH_DETECTED')
      v.setMicState('idle')
    }
  }, NO_TRANSCRIPT_TIMEOUT_MS)
}

export function stopVoice(): void {
  log('stop_voice')
  const vs = useVoiceStore.getState()
  const currentState = vs.micState

  if (currentState === 'listening' || currentState === 'recording') {
    // Tap-to-stop with segments already collected: commit + dispatch immediately
    if (hasTurnActive()) {
      const turn = getCurrentTurn()
      if (turn && turn.finalSegments.length > 0) {
        const committed = commitTurn()
        if (committed && committed.assembledText) {
          log('[VoiceTurn] tap_to_stop_commit', committed.voiceTurnId)
          finalizeMic()
          _dispatchCommittedTurn(committed)
          return
        }
      }
    }
    // No segments yet — server STT still pending. Send mic_stop and wait
    // for the transcript to arrive. The turn stays active so the transcript
    // handler can append the segment and dispatch via silence timer.
    finalizeMic()
    return
  }

  if (client) {
    client.stopMic()
  }
  cancelTurn()
  useChatStore.getState().setDraftMessage(null)
  clearAllTimers()
  vs.setMicState('idle')
  vs.setAudioLevel(0)
  vs.setVadActive(false)
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
  cancelTurn()
  useChatStore.getState().setDraftMessage(null)
  cleanups.forEach(fn => fn())
  cleanups = []
  if (chatUnsub) {
    chatUnsub()
    chatUnsub = null
  }
  releaseHeldMessage()
  resetPlayback()
  _pendingVoiceTurnId = null
  if (client) {
    client.disconnect()
    client = null
  }
}
