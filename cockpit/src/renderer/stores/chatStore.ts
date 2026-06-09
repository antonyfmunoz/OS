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

export interface SuggestedAction {
  label: string
  action: string
  payload: Record<string, unknown>
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
  suggested_actions?: SuggestedAction[]
  metadata?: Record<string, unknown>
}

interface ChatResponse {
  message_id: string
  text: string
  response?: string
  conversation_id: string
  intent: string
  suggested_actions: SuggestedAction[]
  metadata: Record<string, unknown>
  timestamp: string
}

interface ChatState {
  messages: ChatMessage[]
  input: string
  sending: boolean
  error: string | null
  targetChannel: string
  conversationId: string
  _pollTimer: ReturnType<typeof setInterval> | null
  /** Draft message shown during voice recording (live updating "YOU is speaking...") */
  draftMessage: ChatMessage | null
  /** Placeholder message for "DEX is thinking..." during voice flow */
  placeholderMessage: ChatMessage | null

  setInput: (input: string) => void
  setTargetChannel: (channel: string) => void
  sendMessage: (content: string, source?: 'text' | 'voice', viewContext?: Record<string, unknown>, voiceTurnId?: string) => Promise<void>
  loadHistory: () => Promise<void>
  startPolling: () => void
  stopPolling: () => void
  addVoiceTranscript: (text: string, voiceTurnId?: string) => void
  pushExternalMessage: (msg: ChatMessage) => void
  removeMessage: (id: string) => void
  setDraftMessage: (msg: ChatMessage | null) => void
  commitDraftMessage: () => void
  setPlaceholderMessage: (msg: ChatMessage | null) => void
  clearPlaceholderMessage: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  input: '',
  sending: false,
  error: null,
  targetChannel: 'cockpit',
  conversationId: '',
  _pollTimer: null,
  draftMessage: null,
  placeholderMessage: null,

  setInput: (input) => set({ input }),
  setTargetChannel: (channel) => set({ targetChannel: channel }),

  sendMessage: async (content, source = 'text', viewContext?: Record<string, unknown>, voiceTurnId?: string) => {
    if (!content.trim()) return

    const { targetChannel, conversationId } = get()

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
        // Build routing metadata for voice requests
        let routing: Record<string, string> | undefined
        if (source === 'voice') {
          try {
            // eslint-disable-next-line @typescript-eslint/no-var-requires
            const { useDeviceSessionStore } = require('../stores/deviceSessionStore')
            routing = useDeviceSessionStore.getState().getRoutingMetadata() as Record<string, string>
          } catch {
            // routing is optional — degrade gracefully
          }
        }

        const res = await fetchApi<ChatResponse>('/advisor/converse', {
          method: 'POST',
          body: JSON.stringify({
            content: content.trim(),
            view_context: viewContext,
            conversation_id: conversationId,
            source,
            ...(routing ? { routing } : {}),
            ...(voiceTurnId ? { voice_turn_id: voiceTurnId } : {}),
          }),
        })

        const responseText = res.text || (typeof res.response === 'string' ? res.response : '')

        const aiMsg: ChatMessage = {
          id: res.message_id || `ai-${Date.now()}`,
          sender: 'assistant',
          content: responseText,
          timestamp: res.timestamp,
          origin_channel: 'cockpit',
          intent: res.intent,
          suggested_actions: res.suggested_actions,
          metadata: res.metadata,
        }

        set((s) => ({
          messages: [...s.messages, aiMsg],
          sending: false,
          conversationId: res.conversation_id || s.conversationId,
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

      const serverMsgs: ChatMessage[] = history.map((m) => ({
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

      set((s) => {
        const serverIds = new Set(serverMsgs.map((m) => m.id))
        const local = s.messages.filter(
          (m) => !m.id.startsWith('h-') && !serverIds.has(m.id),
        )
        return { messages: [...serverMsgs, ...local] }
      })
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

  addVoiceTranscript: (text, voiceTurnId) => {
    try {
      const { useViewContextStore } = require('../stores/viewContextStore')
      const viewContext = useViewContextStore.getState().context
      get().sendMessage(text, 'voice', viewContext as Record<string, unknown>, voiceTurnId)
    } catch {
      get().sendMessage(text, 'voice', undefined, voiceTurnId)
    }
  },

  pushExternalMessage: (msg) => {
    set((s) => {
      if (s.messages.some((m) => m.id === msg.id)) return s
      return { messages: [...s.messages, msg] }
    })
  },

  removeMessage: (id) => {
    set((s) => ({ messages: s.messages.filter((m) => m.id !== id) }))
  },

  setDraftMessage: (msg) => set({ draftMessage: msg }),

  commitDraftMessage: () => {
    const { draftMessage } = get()
    if (!draftMessage) return
    set((s) => {
      if (s.messages.some((m) => m.id === draftMessage.id)) {
        return { draftMessage: null }
      }
      return {
        messages: [...s.messages, draftMessage],
        draftMessage: null,
      }
    })
  },

  setPlaceholderMessage: (msg) => set({ placeholderMessage: msg }),

  clearPlaceholderMessage: () => set({ placeholderMessage: null }),
}))
