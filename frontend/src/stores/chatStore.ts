import { create } from 'zustand'
import { fetchApi } from '../api/client'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  modelUsed?: string
  durationMs?: number
}

interface ChatState {
  messages: ChatMessage[]
  isLoading: boolean
  sendMessage: (text: string) => Promise<void>
  clearMessages: () => void
}

let messageCounter = 0

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isLoading: false,

  sendMessage: async (text: string) => {
    const userMsg: ChatMessage = {
      id: `msg-${++messageCounter}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    }

    set((state) => ({
      messages: [...state.messages, userMsg],
      isLoading: true,
    }))

    try {
      const response = await fetchApi<{
        text: string
        model_used: string
        duration_ms: number
      }>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message: text }),
      })

      const assistantMsg: ChatMessage = {
        id: `msg-${++messageCounter}`,
        role: 'assistant',
        content: response.text,
        timestamp: new Date().toISOString(),
        modelUsed: response.model_used,
        durationMs: response.duration_ms,
      }

      set((state) => ({
        messages: [...state.messages, assistantMsg],
        isLoading: false,
      }))
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: `msg-${++messageCounter}`,
        role: 'system',
        content: `Error: ${err instanceof Error ? err.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      }

      set((state) => ({
        messages: [...state.messages, errorMsg],
        isLoading: false,
      }))
    }
  },

  clearMessages: () => set({ messages: [] }),
}))
