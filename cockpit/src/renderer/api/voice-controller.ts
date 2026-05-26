import { VoiceWsClient } from './voice-ws'
import { useVoiceStore } from '../stores/voiceStore'
import { useChatStore } from '../stores/chatStore'

let client: VoiceWsClient | null = null
let cleanups: (() => void)[] = []

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
  const store = useVoiceStore.getState()

  cleanups.push(
    client.on('connected', () => {
      console.log('[Voice] Connected to voice server')
    })
  )

  cleanups.push(
    client.on('disconnected', () => {
      store.setMicState('idle')
      store.setTtsState('idle')
      store.setAudioLevel(0)
    })
  )

  cleanups.push(
    client.on('vad_status', (data) => {
      const active = data.active as boolean
      store.setVadActive(active)
      store.setMicState(active ? 'listening' : 'idle')
    })
  )

  cleanups.push(
    client.on('audio_level', (data) => {
      store.setAudioLevel(data.level as number)
    })
  )

  cleanups.push(
    client.on('transcript', (data) => {
      const text = data.text as string
      const final = data.final as boolean
      store.setLastTranscript(text)
      if (final && text) {
        store.setMicState('processing')
      }
    })
  )

  cleanups.push(
    client.on('tts_status', (data) => {
      store.setTtsState((data.speaking as boolean) ? 'speaking' : 'idle')
    })
  )

  cleanups.push(
    client.on('voice_response', (data) => {
      const text = data.text as string
      if (text) {
        useChatStore.getState().addVoiceTranscript(text)
      }
      store.setMicState('idle')
    })
  )
}

export async function startVoice(): Promise<void> {
  const c = getClient()
  useVoiceStore.getState().setMicState('listening')
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

export function destroyVoice(): void {
  cleanups.forEach(fn => fn())
  cleanups = []
  if (client) {
    client.disconnect()
    client = null
  }
}
