import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface ChatMessage {
  id: string
  sender: 'operator' | 'dex'
  content: string
  timestamp: string
  source?: 'text' | 'voice'
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

  setInput: (input: string) => void
  sendMessage: (content: string, source?: 'text' | 'voice') => Promise<void>
  loadHistory: () => Promise<void>
  addVoiceTranscript: (text: string) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  input: '',
  sending: false,
  error: null,

  setInput: (input) => set({ input }),

  sendMessage: async (content, source = 'text') => {
    if (!content.trim()) return

    const operatorMsg: ChatMessage = {
      id: `op-${Date.now()}`,
      sender: 'operator',
      content: content.trim(),
      timestamp: new Date().toISOString(),
      source,
    }

    set((s) => ({
      messages: [...s.messages, operatorMsg],
      input: '',
      sending: true,
      error: null,
    }))

    try {
      const res = await fetchApi<DexResponse>('/api/umh/dex/converse', {
        method: 'POST',
        body: JSON.stringify({ content: content.trim() }),
      })

      const dexMsg: ChatMessage = {
        id: res.message_id,
        sender: 'dex',
        content: typeof res.response === 'string' ? res.response : JSON.stringify(res.response),
        timestamp: res.timestamp,
      }

      set((s) => ({
        messages: [...s.messages, dexMsg],
        sending: false,
      }))
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
        content: string
        response: string | null
        timestamp: string
      }>>('/api/umh/dex/history?limit=50')

      const messages: ChatMessage[] = []
      for (const exchange of history) {
        if (exchange.content) {
          messages.push({
            id: `h-op-${exchange.id}`,
            sender: 'operator',
            content: exchange.content,
            timestamp: exchange.timestamp,
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
}))
