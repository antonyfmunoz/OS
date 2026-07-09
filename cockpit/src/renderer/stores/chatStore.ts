import { create } from 'zustand'
import { fetchApi, API_BASE, authHeader } from '../api/client'

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
  media_type: 'image' | 'video' | 'audio' | 'file'
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
  media_type: 'image' | 'video' | 'audio' | 'file'
}

/**
 * Voice-message send extras. When present, `media` (the uploaded audio
 * artifact) is attached to the operator ChatMessage and `meta` is carried in
 * the /advisor/converse body as `voice_message` so the intent-loop handoff
 * threads {draft_id, artifact_id, duration_ms, transcript_status,
 * consent_grant_id}. The finalized transcript text is the message content
 * verbatim — meta NEVER substitutes for it.
 */
export interface VoiceTranscriptOptions {
  media?: MediaAttachment[]
  meta?: Record<string, unknown>
}

interface SendMessageOptions {
  media?: MediaAttachment[]
  voiceMessage?: Record<string, unknown>
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
  sendMessage: (content: string, source?: 'text' | 'voice', viewContext?: Record<string, unknown>, voiceTurnId?: string, opts?: SendMessageOptions) => Promise<void>
  loadHistory: () => Promise<void>
  startPolling: () => void
  stopPolling: () => void
  addVoiceTranscript: (text: string, voiceTurnId?: string, opts?: VoiceTranscriptOptions) => void
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

  sendMessage: async (content, source = 'text', viewContext?: Record<string, unknown>, voiceTurnId?: string, opts?: SendMessageOptions) => {
    const { targetChannel, conversationId, pendingMedia } = get()
    // Pre-uploaded media (e.g. the voice audio artifact) still counts as content.
    const preUploaded = opts?.media ?? []
    if (!content.trim() && pendingMedia.length === 0 && preUploaded.length === 0) return

    // Synchronous re-entrancy guard: a second Enter/click before the first send
    // resolves must no-op. `sending` was only set AFTER the media-upload await, so a
    // rapid double-submit slipped two messages through (field test 2026-07-08). Claim
    // the latch here, before any await, and release it in the catch/finally paths.
    if (get().sending) return
    set({ sending: true })

    let uploadedMedia: MediaAttachment[] = [...preUploaded]
    if (pendingMedia.length > 0) {
      try {
        const uploads = await Promise.all(
          pendingMedia.map(async (pm) => {
            const form = new FormData()
            form.append('file', pm.file)
            const res = await fetch(`${API_BASE}/chat/upload`, {
              method: 'POST',
              body: form,
              headers: await authHeader(), // operator-gated route — send Clerk bearer or 403
            })
            if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`)
            return res.json() as Promise<MediaAttachment>
          }),
        )
        uploadedMedia = [...uploadedMedia, ...uploads.map((u, i) => ({ ...u, previewUrl: pendingMedia[i].previewUrl }))]
      } catch (e) {
        // Release the sending latch so the input isn't permanently frozen on an
        // upload failure — the operator can correct and resend.
        set({ error: e instanceof Error ? e.message : 'Media upload failed', sending: false })
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
            ...(opts?.voiceMessage ? { voice_message: opts.voiceMessage } : {}),
            // Persist the operator's media (e.g. a voice message's audio) on the turn
            // so it survives reload — the server stores it and /chat/history returns it.
            ...(uploadedMedia.length > 0 ? { media: uploadedMedia } : {}),
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
        media?: MediaAttachment[]
        source?: 'text' | 'voice'
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
        // Voice messages persist their audio player across reload: history returns the
        // stored media so MediaGrid/VoiceMessagePlayer render just like the live message.
        ...(m.media ? { media: m.media } : {}),
        // Keep source ("voice") so the reloaded h-* message still shows the voice badge
        // + transcript chevron (OperatorBubble gates them on source === 'voice').
        ...(m.source ? { source: m.source } : {}),
      }))

      set((s) => {
        const serverIds = new Set(serverMsgs.map((m) => m.id))
        // Reconcile optimistic local messages (op-*/ai-* with a client-generated id)
        // against their persisted history twins (h-*). The server returns no
        // correlation id, and op-<ts> can NEVER equal h-<serverid>, so id-only dedup
        // let the SAME operator message render twice — once optimistic, once from the
        // 30s history poll (field test 2026-07-08: duplicate voice bubble). Match on a
        // content key, but CONSUME each server key ONCE (a multiset, not a set): two
        // distinct sends with the same transcript ("yes", "test") each have their own
        // server twin, so dropping BOTH locals on one server row would make a real
        // message vanish. One server occurrence dedups exactly one local twin.
        const contentKey = (m: ChatMessage) =>
          `${m.sender}|${(m.content || '').trim()}|${m.media?.length ? 'm' + m.media.length : ''}`
        const serverKeyCounts = new Map<string, number>()
        for (const sm of serverMsgs) {
          const k = contentKey(sm)
          serverKeyCounts.set(k, (serverKeyCounts.get(k) ?? 0) + 1)
        }
        const local = s.messages.filter((m) => {
          if (m.id.startsWith('h-') || serverIds.has(m.id)) return false
          const k = contentKey(m)
          const remaining = serverKeyCounts.get(k) ?? 0
          if (remaining > 0) {
            serverKeyCounts.set(k, remaining - 1) // consume one twin, keep the rest
            return false
          }
          return true
        })
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

  addVoiceTranscript: (text, voiceTurnId, opts) => {
    // The finalized transcript text is the message content VERBATIM. When
    // opts.media/opts.meta are present (explicit send of a voice draft), the
    // audio artifact rides as media and meta becomes the converse body's
    // `voice_message` for the intent-loop handoff. 2-arg callers keep working.
    const sendOpts: SendMessageOptions | undefined =
      opts && (opts.media?.length || opts.meta)
        ? { media: opts.media, voiceMessage: opts.meta }
        : undefined
    try {
      const { useViewContextStore } = require('../stores/viewContextStore')
      const viewContext = useViewContextStore.getState().context
      get().sendMessage(text, 'voice', viewContext as Record<string, unknown>, voiceTurnId, sendOpts)
    } catch {
      get().sendMessage(text, 'voice', undefined, voiceTurnId, sendOpts)
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
      media_type: f.type.startsWith('video/') ? 'video' : f.type.startsWith('image/') ? 'image' : f.type.startsWith('audio/') ? 'audio' : 'file',
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
