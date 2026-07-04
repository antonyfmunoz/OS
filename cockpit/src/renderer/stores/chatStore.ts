import { create } from 'zustand'
import { fetchApi, API_BASE } from '../api/client'

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

export interface MediaAttachment {
  id: string
  url: string
  filename: string
  content_type: string
  media_type: 'image' | 'video' | 'file'
  size: number
  previewUrl?: string
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
  media?: MediaAttachment[]
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

interface PendingMedia {
  file: File
  previewUrl: string
  media_type: 'image' | 'video' | 'file'
}

interface ChatState {
  messages: ChatMessage[]
  input: string
  sending: boolean
  error: string | null
  targetChannel: string
  conversationId: string
  _pollTimer: ReturnType<typeof setInterval> | null
  draftMessage: ChatMessage | null
  placeholderMessage: ChatMessage | null
  pendingMedia: PendingMedia[]

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
  addPendingMedia: (files: File[]) => void
  removePendingMedia: (index: number) => void
  clearPendingMedia: () => void
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
  pendingMedia: [],

  setInput: (input) => set({ input }),
  setTargetChannel: (channel) => set({ targetChannel: channel }),

  sendMessage: async (content, source = 'text', viewContext?: Record<string, unknown>, voiceTurnId?: string) => {
    const { targetChannel, conversationId, pendingMedia } = get()
    if (!content.trim() && pendingMedia.length === 0) return

    let uploadedMedia: MediaAttachment[] = []
    if (pendingMedia.length > 0) {
      try {
        const uploads = await Promise.all(
          pendingMedia.map(async (pm) => {
            const form = new FormData()
            form.append('file', pm.file)
            const res = await fetch(`${API_BASE}/chat/upload`, {
              method: 'POST',
              body: form,
            })
            if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`)
            return res.json() as Promise<MediaAttachment>
          }),
        )
        uploadedMedia = uploads.map((u, i) => ({ ...u, previewUrl: pendingMedia[i].previewUrl }))
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Media upload failed' })
        return
      }
    }

    const operatorMsg: ChatMessage = {
      id: `op-${Date.now()}`,
      sender: 'operator',
      content: content.trim(),
      timestamp: new Date().toISOString(),
      source,
      origin_channel: targetChannel,
      ...(uploadedMedia.length > 0 ? { media: uploadedMedia } : {}),
    }

    pendingMedia.forEach((pm) => URL.revokeObjectURL(pm.previewUrl))

    set((s) => ({
      messages: [...s.messages, operatorMsg],
      input: '',
      sending: true,
      error: null,
      pendingMedia: [],
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

  addPendingMedia: (files) => {
    if (files.length === 0) return
    const items: PendingMedia[] = files.map((f) => ({
      file: f,
      previewUrl: f.type.startsWith('image/') || f.type.startsWith('video/') ? URL.createObjectURL(f) : '',
      media_type: f.type.startsWith('video/') ? 'video' : f.type.startsWith('image/') ? 'image' : 'file',
    }))
    set((s) => ({ pendingMedia: [...s.pendingMedia, ...items] }))
  },

  removePendingMedia: (index) => {
    set((s) => {
      const item = s.pendingMedia[index]
      if (item) URL.revokeObjectURL(item.previewUrl)
      return { pendingMedia: s.pendingMedia.filter((_, i) => i !== index) }
    })
  },

  clearPendingMedia: () => {
    set((s) => {
      s.pendingMedia.forEach((pm) => URL.revokeObjectURL(pm.previewUrl))
      return { pendingMedia: [] }
    })
  },
}))
