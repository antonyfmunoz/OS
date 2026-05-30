import { create } from 'zustand'
import { fetchApi } from '../api/client'

export interface Provenance {
  node?: string
  harness?: string
  session?: string
  phase?: string
  pr?: number | string
  task?: string
}

export interface Attachment {
  path: string
  filename: string
}

export interface ChatMessage {
  id: string
  sender: 'operator' | 'assistant' | 'system'
  content: string
  timestamp: string
  source?: 'text' | 'voice'
  origin_channel?: string
  intent?: string
  title?: string
  provenance?: Provenance
  attachment?: Attachment
}

interface ChatResponse {
  message_id: string
  response: string
  timestamp: string
}

interface ChatState {
  messages: ChatMessage[]
  input: string
  sending: boolean
  error: string | null
  targetChannel: string
  _pollTimer: ReturnType<typeof setInterval> | null

  setInput: (input: string) => void
  setTargetChannel: (channel: string) => void
  sendMessage: (content: string, source?: 'text' | 'voice') => Promise<void>
  loadHistory: () => Promise<void>
  startPolling: () => void
  stopPolling: () => void
  addVoiceTranscript: (text: string) => void
  pushExternalMessage: (msg: ChatMessage) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  input: '',
  sending: false,
  error: null,
  targetChannel: 'cockpit',
  _pollTimer: null,

  setInput: (input) => set({ input }),
  setTargetChannel: (channel) => set({ targetChannel: channel }),

  sendMessage: async (content, source = 'text') => {
    if (!content.trim()) return

    const { targetChannel } = get()

    const operatorMsg: ChatMessage = {
      id: `op-${Date.now()}`,
      sender: 'operator',
      content: content.trim(),
      timestamp: new Date().toISOString(),
      source,
      origin_channel: targetChannel,
    }

    set((s) => ({
      messages: [...s.messages, operatorMsg],
      input: '',
      sending: true,
      error: null,
    }))

    try {
      if (targetChannel === 'cockpit') {
        const res = await fetchApi<ChatResponse>('/dex/converse', {
          method: 'POST',
          body: JSON.stringify({ content: content.trim() }),
        })

        const aiMsg: ChatMessage = {
          id: res.message_id,
          sender: 'assistant',
          content: typeof res.response === 'string' ? res.response : JSON.stringify(res.response),
          timestamp: res.timestamp,
          origin_channel: 'cockpit',
        }

        set((s) => ({
          messages: [...s.messages, aiMsg],
          sending: false,
        }))
      } else {
        await fetchApi('/chat/send', {
          method: 'POST',
          body: JSON.stringify({ channel: targetChannel, content: content.trim() }),
        })
        set({ sending: false })
      }
    } catch (e) {
      set({
        sending: false,
        error: e instanceof Error ? e.message : 'Failed to reach assistant',
      })
    }
  },

  loadHistory: async () => {
    try {
      const history = await fetchApi<Array<{
        id: string
        sender: string
        content: string
        timestamp: string
        origin_channel?: string
        intent?: string
        title?: string
        provenance?: Provenance
        attachment?: Attachment
      }>>('/chat/history')

      const messages: ChatMessage[] = history.map((m) => ({
        id: `h-${m.id}`,
        sender: (m.sender === 'operator' ? 'operator' : 'assistant') as ChatMessage['sender'],
        content: m.content,
        timestamp: m.timestamp,
        origin_channel: m.origin_channel,
        intent: m.intent as ChatMessage['intent'],
        title: m.title,
        provenance: m.provenance,
        attachment: m.attachment,
      }))
      set({ messages })
    } catch {
      // History load failure is non-critical
    }
  },

  startPolling: () => {
    const { _pollTimer, loadHistory } = get()
    if (_pollTimer) return
    const timer = setInterval(() => { loadHistory() }, 30_000)
    set({ _pollTimer: timer })
  },

  stopPolling: () => {
    const { _pollTimer } = get()
    if (_pollTimer) {
      clearInterval(_pollTimer)
      set({ _pollTimer: null })
    }
  },

  addVoiceTranscript: (text) => {
    get().sendMessage(text, 'voice')
  },

  pushExternalMessage: (msg) => {
    set((s) => {
      if (s.messages.some((m) => m.id === msg.id)) return s
      return { messages: [...s.messages, msg] }
    })
  },
}))
