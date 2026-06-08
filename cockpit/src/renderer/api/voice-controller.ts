import { VoiceWsClient } from './voice-ws'
import { useVoiceStore } from '../stores/voiceStore'
import { useChatStore } from '../stores/chatStore'

let client: VoiceWsClient | null = null
let cleanups: (() => void)[] = []
let chatUnsub: (() => void) | null = null

function getClient(): VoiceWsClient {
  if (!client) {
    client = new VoiceWsClient()
    wireEvents()
    client.connect()
  }
  return client
}

function wireEvents(): void {
  if (!client) return

  cleanups.push(
    client.on('connected', () => {
      console.log('[Voice] Connected to voice server')
    })
  )

  cleanups.push(
    client.on('disconnected', () => {
      useVoiceStore.getState().setMicState('idle')
      useVoiceStore.getState().setTtsState('idle')
      useVoiceStore.getState().setAudioLevel(0)
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
        voiceStore.setMicState('listening')
      } else {
        voiceStore.setMicState(active ? 'listening' : 'idle')
      }
    })
  )

  cleanups.push(
    client.on('audio_level', (data) => {
      useVoiceStore.getState().setAudioLevel(data.level as number)
    })
  )

  cleanups.push(
    client.on('transcript', (data) => {
      const text = data.text as string
      const isFinal = data.final as boolean
      useVoiceStore.getState().setLastTranscript(text)
      if (isFinal && text) {
        useVoiceStore.getState().setMicState('processing')
        useVoiceStore.getState().setPendingVoiceResponse(true)
        useChatStore.getState().addVoiceTranscript(text)
      }
    })
  )

  cleanups.push(
    client.on('tts_status', (data) => {
      useVoiceStore.getState().setTtsState((data.speaking as boolean) ? 'speaking' : 'idle')
    })
  )

  cleanups.push(
    client.on('tts_error', (data) => {
      useVoiceStore.getState().setError(data.error as string)
      useVoiceStore.getState().setTtsState('idle')
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

    voiceState.setPendingVoiceResponse(false)
    voiceState.setMicState('listening')
    if (client && last.content) {
      client.requestTts(last.content)
    }
  })
}

export async function startVoice(): Promise<void> {
  const c = getClient()
  useVoiceStore.getState().setMicState('listening')
  useVoiceStore.getState().setError(null)
  await c.startMic()
}

export function stopVoice(): void {
  if (client) {
    client.stopMic()
  }
  const store = useVoiceStore.getState()
  store.setMicState('idle')
  store.setAudioLevel(0)
  store.setVadActive(false)
}

export function speakResponse(text: string): void {
  const c = getClient()
  c.requestTts(text)
}

export function stopTts(): void {
  if (client) {
    client.cancelTts()
  }
  useVoiceStore.getState().setTtsState('idle')
}

export function destroyVoice(): void {
  cleanups.forEach(fn => fn())
  cleanups = []
  if (chatUnsub) {
    chatUnsub()
    chatUnsub = null
  }
  if (client) {
    client.disconnect()
    client = null
  }
}
