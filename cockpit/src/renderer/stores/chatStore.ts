import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface ChatMessage {
  id: string
  sender: 'operator' | 'dex' | 'system'
  content: string
  timestamp: string
  source?: 'text' | 'voice'
  origin_channel?: string
}

interface DexResponse {
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

  setInput: (input: string) => void
  setTargetChannel: (channel: string) => void
  sendMessage: (content: string, source?: 'text' | 'voice') => Promise<void>
  loadHistory: () => Promise<void>
  addVoiceTranscript: (text: string) => void
  pushExternalMessage: (msg: ChatMessage) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  input: '',
  sending: false,
  error: null,
  targetChannel: 'cockpit',

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
        const res = await fetchApi<DexResponse>('/chat/converse', {
          method: 'POST',
          body: JSON.stringify({ content: content.trim() }),
        })

        const dexMsg: ChatMessage = {
          id: res.message_id,
          sender: 'dex',
          content: typeof res.response === 'string' ? res.response : JSON.stringify(res.response),
          timestamp: res.timestamp,
          origin_channel: 'cockpit',
        }

        set((s) => ({
          messages: [...s.messages, dexMsg],
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
        error: e instanceof Error ? e.message : 'Failed to reach DEX',
      })
    }
  },

  loadHistory: async () => {
    try {
      const history = await fetchApi<Array<{
        id: string
        sender?: string
        content: string
        response: string | null
        timestamp: string
        origin_channel?: string
      }>>('/chat/history?limit=50')

      const messages: ChatMessage[] = []
      for (const exchange of history) {
        if (exchange.sender === 'system') {
          messages.push({
            id: `h-sys-${exchange.id}`,
            sender: 'system',
            content: exchange.content,
            timestamp: exchange.timestamp,
            origin_channel: exchange.origin_channel,
          })
          continue
        }
        if (exchange.content) {
          messages.push({
            id: `h-op-${exchange.id}`,
            sender: 'operator',
            content: exchange.content,
            timestamp: exchange.timestamp,
            origin_channel: exchange.origin_channel,
          })
        }
        if (exchange.response) {
          messages.push({
            id: `h-dex-${exchange.id}`,
            sender: 'dex',
            content: typeof exchange.response === 'string'
              ? exchange.response
              : JSON.stringify(exchange.response),
            timestamp: exchange.timestamp,
            origin_channel: exchange.origin_channel,
          })
        }
      }
      set({ messages })
    } catch {
      // History load failure is non-critical
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
