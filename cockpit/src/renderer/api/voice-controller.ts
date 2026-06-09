import { VoiceWsClient } from './voice-ws'
import { useVoiceStore } from '../stores/voiceStore'
import { useChatStore } from '../stores/chatStore'

let client: VoiceWsClient | null = null
let cleanups: (() => void)[] = []
let chatUnsub: (() => void) | null = null
let pendingTimeout: ReturnType<typeof setTimeout> | null = null
let noSpeechTimeout: ReturnType<typeof setTimeout> | null = null
let maxRecordingTimeout: ReturnType<typeof setTimeout> | null = null
let heldVoiceMessage: { id: string; content: string } | null = null

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
        client?.cancelTts()
        voiceStore.setTtsState('idle')
        voiceStore.setMicState('interrupted')
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

      clearAllTimers()
      const vs = useVoiceStore.getState()
      vs.setLastTranscript(text)

      if (isFinal) {
        if (!text.trim()) {
          log('no_speech_in_transcript')
          vs.setError('No speech detected — try again')
          vs.setLastOutcome('NO_SPEECH_DETECTED')
          vs.setMicState('idle')
          return
        }

        vs.setMicState('transcribing')
        log('transcript_dispatching', text.slice(0, 80))

        setTimeout(() => {
          const vs2 = useVoiceStore.getState()
          vs2.setMicState('processing')
          vs2.setPendingVoiceResponse(true)
          vs2.setError(null)
          vs2.setLastOutcome('TRANSCRIPT_RECEIVED')
          useChatStore.getState().addVoiceTranscript(text)
          log('transcript_dispatched_to_chat')

          pendingTimeout = setTimeout(() => {
            const v = useVoiceStore.getState()
            if (v.pendingVoiceResponse) {
              v.setPendingVoiceResponse(false)
              v.setMicState('idle')
              v.setError('Response timed out — try again')
              v.setLastOutcome('TIMEOUT')
              releaseHeldMessage()
              log('response_timeout')
            }
          }, PENDING_RESPONSE_TIMEOUT_MS)
        }, 100)
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

    if (client && last.content) {
      voiceState.setTtsState('generating_tts')
      heldVoiceMessage = null

      const ttsTimeout = setTimeout(() => {
        const v = useVoiceStore.getState()
        if (v.ttsState === 'generating_tts') {
          log('tts_generate_timeout')
          v.setTtsState('tts_failed')
          v.setError('Voice generation timed out — showing text')
          releaseHeldMessage()
          setTimeout(() => useVoiceStore.getState().setTtsState('idle'), 3000)
        }
      }, TTS_GENERATE_TIMEOUT_MS)

      client.requestTts(last.content)

      cleanups.push(() => clearTimeout(ttsTimeout))
    }
  })
}

export async function startVoice(): Promise<void> {
  const vs = useVoiceStore.getState()
  vs.setError(null)
  vs.setLastOutcome(null)
  vs.setChunksSent(0)
  clearAllTimers()

  log('mic_clicked')

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
    finalizeMic()
    return
  }

  if (client) {
    client.stopMic()
  }
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
  useVoiceStore.getState().setTtsState('idle')
  releaseHeldMessage()
}

export function destroyVoice(): void {
  clearAllTimers()
  cleanups.forEach(fn => fn())
  cleanups = []
  if (chatUnsub) {
    chatUnsub()
    chatUnsub = null
  }
  releaseHeldMessage()
  if (client) {
    client.disconnect()
    client = null
  }
}
