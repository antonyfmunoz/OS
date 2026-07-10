import { create } from 'zustand'
import { fetchApi } from '../api/client'
import { useConfigStore } from './configStore'
import { DEFAULT_GUEST_PERMISSIONS } from '../types/rooms'
import type {
  RoomServer,
  ServerCategory,
  RoomChannel,
  RoomMessage,
  RoomThread,
  ForumPost,
  ForumTag,
  RoomRole,
  RoomMember,
  RoomInvite,
  GuestPermissions,
  MeetingState,
  VoiceRoomState,
  RoomEvent,
  RoomArtifact,
  DexRoomSettings,
  RoomSearchResult,
  ChannelType,
  ServerPrivacy,
  ServerTemplate,
  DexRoomMode,
  MeetingMode,
  PresenceStatus,
  RoomPermission,
  MeetingActionItem,
} from '../types/rooms'

const API = '/rooms'

export interface CreateInviteOptions {
  channel_id: string | null
  room_type: 'voice' | 'meeting'
  label?: string | null
  max_uses?: number | null
  expires_hours?: number | null
  allowed_email_domains?: string[] | null
  allowed_emails?: string[] | null
  permissions?: Partial<GuestPermissions>
}

interface RoomsState {
  servers: RoomServer[]
  activeServerId: string | null
  categories: ServerCategory[]
  channels: RoomChannel[]
  activeChannelId: string | null
  messages: RoomMessage[]
  threads: RoomThread[]
  forumPosts: ForumPost[]
  forumTags: ForumTag[]
  roles: RoomRole[]
  members: RoomMember[]
  invites: RoomInvite[]
  meetingStates: Record<string, MeetingState>
  voiceStates: Record<string, VoiceRoomState>
  auditLog: RoomEvent[]
  artifacts: RoomArtifact[]
  dexSettings: Record<string, DexRoomSettings>
  searchResults: RoomSearchResult[]
  typingUsers: Record<string, string[]>

  loading: boolean
  error: string | null
  messagesLoading: boolean
  hasMoreMessages: boolean

  // Server actions
  fetchServers: () => Promise<void>
  createServer: (name: string, description: string, privacy: ServerPrivacy, template: ServerTemplate | null) => Promise<RoomServer | null>
  updateServer: (id: string, updates: Partial<Pick<RoomServer, 'name' | 'description' | 'icon_emoji' | 'privacy' | 'archived' | 'sort_order' | 'pinned'>>) => Promise<void>
  deleteServer: (id: string) => Promise<void>
  setActiveServer: (id: string | null) => void

  // Category actions
  fetchCategories: (serverId: string) => Promise<void>
  createCategory: (serverId: string, name: string) => Promise<ServerCategory | null>
  updateCategory: (id: string, updates: Partial<Pick<ServerCategory, 'name' | 'sort_order' | 'collapsed' | 'muted' | 'permission_synced'>>) => Promise<void>
  deleteCategory: (id: string) => Promise<void>

  // Channel actions
  fetchChannels: (serverId: string) => Promise<void>
  createChannel: (serverId: string, categoryId: string | null, name: string, type: ChannelType) => Promise<RoomChannel | null>
  updateChannel: (id: string, updates: Partial<Pick<RoomChannel, 'name' | 'topic' | 'sort_order' | 'private' | 'locked' | 'slowmode_seconds' | 'archived' | 'muted' | 'dex_mode' | 'dex_enabled' | 'memory_scope'>>) => Promise<void>
  deleteChannel: (id: string) => Promise<void>
  setActiveChannel: (id: string | null) => void

  // Message actions
  fetchMessages: (channelId: string, before?: string) => Promise<void>
  sendMessage: (channelId: string, content: string, replyToId?: string) => Promise<RoomMessage | null>
  editMessage: (id: string, content: string) => Promise<void>
  deleteMessage: (id: string) => Promise<void>
  pinMessage: (id: string, pinned: boolean) => Promise<void>
  addReaction: (messageId: string, emoji: string) => Promise<void>
  removeReaction: (messageId: string, emoji: string) => Promise<void>

  // Thread actions
  fetchThreads: (channelId: string) => Promise<void>
  createThread: (channelId: string, name: string, parentMessageId?: string) => Promise<RoomThread | null>
  updateThread: (id: string, updates: Partial<Pick<RoomThread, 'name' | 'archived' | 'locked'>>) => Promise<void>

  // Forum actions
  fetchForumPosts: (channelId: string) => Promise<void>
  createForumPost: (channelId: string, title: string, body: string, tags: string[]) => Promise<ForumPost | null>
  updateForumPost: (id: string, updates: Partial<Pick<ForumPost, 'title' | 'body' | 'tags' | 'pinned' | 'locked' | 'closed'>>) => Promise<void>
  fetchForumTags: (channelId: string) => Promise<void>
  createForumTag: (channelId: string, name: string, color: string) => Promise<void>

  // Role actions
  fetchRoles: (serverId: string) => Promise<void>
  createRole: (serverId: string, name: string, color: string, permissions: RoomPermission[]) => Promise<RoomRole | null>
  updateRole: (id: string, updates: Partial<Pick<RoomRole, 'name' | 'color' | 'icon_emoji' | 'sort_order' | 'permissions'>>) => Promise<void>
  deleteRole: (id: string) => Promise<void>

  // Member actions
  fetchMembers: (serverId: string) => Promise<void>
  assignRole: (serverId: string, userId: string, roleId: string) => Promise<void>
  removeRole: (serverId: string, userId: string, roleId: string) => Promise<void>
  updatePresence: (status: PresenceStatus) => Promise<void>

  // Invite actions
  fetchInvites: (serverId: string) => Promise<void>
  createInvite: (serverId: string, opts: CreateInviteOptions) => Promise<RoomInvite | null>
  revokeInvite: (id: string) => Promise<void>

  // Meeting actions
  fetchMeeting: (channelId: string) => Promise<void>
  updateMeeting: (channelId: string, updates: Partial<Pick<MeetingState, 'objective' | 'agenda' | 'notes' | 'decisions' | 'mode' | 'recording_consent' | 'ai_assistance'>>) => Promise<void>
  addMeetingActionItem: (channelId: string, item: Omit<MeetingActionItem, 'id'>) => Promise<void>
  toggleMeetingActionItem: (channelId: string, itemId: string) => Promise<void>
  endMeeting: (channelId: string) => Promise<void>

  // Voice actions
  fetchVoiceState: (channelId: string) => Promise<void>
  joinVoice: (channelId: string) => Promise<void>
  leaveVoice: (channelId: string) => Promise<void>

  // assistant actions
  fetchDexSettings: (channelId: string) => Promise<void>
  updateDexSettings: (channelId: string, updates: Partial<DexRoomSettings>) => Promise<void>
  dexSummarize: (channelId: string) => Promise<string>

  // Audit log
  fetchAuditLog: (serverId: string) => Promise<void>

  // Artifacts
  fetchArtifacts: (channelId: string) => Promise<void>
  createArtifact: (channelId: string, name: string, type: string, metadata: Record<string, unknown>) => Promise<void>

  // Search
  search: (serverId: string, query: string, filters?: Record<string, string>) => Promise<void>

  // Realtime handlers
  handleWsEvent: (event: { type: string; payload: unknown }) => void
  setTyping: (channelId: string, userId: string, typing: boolean) => void
}

const STORAGE_KEY = 'rooms:lastActive'

function loadLastActive(): { serverId: string | null; channelId: string | null } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return { serverId: null, channelId: null }
}

function saveLastActive(serverId: string | null, channelId: string | null) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ serverId, channelId }))
  } catch { /* ignore */ }
}

const lastActive = loadLastActive()

export const useRoomsStore = create<RoomsState>((set, get) => ({
  servers: [],
  activeServerId: lastActive.serverId,
  categories: [],
  channels: [],
  activeChannelId: lastActive.channelId,
  messages: [],
  threads: [],
  forumPosts: [],
  forumTags: [],
  roles: [],
  members: [],
  invites: [],
  meetingStates: {},
  voiceStates: {},
  auditLog: [],
  artifacts: [],
  dexSettings: {},
  searchResults: [],
  typingUsers: {},
  loading: false,
  error: null,
  messagesLoading: false,
  hasMoreMessages: true,

  // ── Server actions ──

  fetchServers: async () => {
    set({ loading: true, error: null })
    try {
      const servers = await fetchApi<RoomServer[]>(`${API}/servers`)
      set({ servers, loading: false })
      const { activeServerId } = get()
      if (activeServerId && servers.some((s) => s.id === activeServerId)) {
        get().fetchCategories(activeServerId)
        get().fetchChannels(activeServerId)
        get().fetchRoles(activeServerId)
        get().fetchMembers(activeServerId)
      } else if (activeServerId) {
        set({ activeServerId: null, activeChannelId: null })
        saveLastActive(null, null)
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch servers', loading: false })
    }
  },

  createServer: async (name, description, privacy, template) => {
    try {
      const server = await fetchApi<RoomServer>(`${API}/servers`, {
        method: 'POST',
        body: JSON.stringify({ name, description, privacy, template }),
      })
      set((s) => ({ servers: [...s.servers, server] }))
      return server
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to create server' })
      return null
    }
  },

  updateServer: async (id, updates) => {
    try {
      const server = await fetchApi<RoomServer>(`${API}/servers/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })
      set((s) => ({ servers: s.servers.map((sv) => (sv.id === id ? server : sv)) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to update server' })
    }
  },

  deleteServer: async (id) => {
    try {
      await fetchApi(`${API}/servers/${id}`, { method: 'DELETE' })
      set((s) => ({
        servers: s.servers.filter((sv) => sv.id !== id),
        activeServerId: s.activeServerId === id ? null : s.activeServerId,
      }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to delete server' })
    }
  },

  setActiveServer: (id) => {
    const saved = loadLastActive()
    const keepChannel = id && saved.serverId === id ? saved.channelId : null
    set({ activeServerId: id, activeChannelId: keepChannel, messages: [], threads: [], forumPosts: [] })
    saveLastActive(id, keepChannel)
    if (id) {
      get().fetchCategories(id)
      get().fetchChannels(id)
      get().fetchRoles(id)
      get().fetchMembers(id)
    }
  },

  // ── Category actions ──

  fetchCategories: async (serverId) => {
    try {
      const categories = await fetchApi<ServerCategory[]>(`${API}/servers/${serverId}/categories`)
      set({ categories })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch categories' })
    }
  },

  createCategory: async (serverId, name) => {
    try {
      const cat = await fetchApi<ServerCategory>(`${API}/servers/${serverId}/categories`, {
        method: 'POST',
        body: JSON.stringify({ name }),
      })
      set((s) => ({ categories: [...s.categories, cat] }))
      return cat
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to create category' })
      return null
    }
  },

  updateCategory: async (id, updates) => {
    try {
      const cat = await fetchApi<ServerCategory>(`${API}/categories/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })
      set((s) => ({ categories: s.categories.map((c) => (c.id === id ? cat : c)) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to update category' })
    }
  },

  deleteCategory: async (id) => {
    try {
      await fetchApi(`${API}/categories/${id}`, { method: 'DELETE' })
      set((s) => ({ categories: s.categories.filter((c) => c.id !== id) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to delete category' })
    }
  },

  // ── Channel actions ──

  fetchChannels: async (serverId) => {
    try {
      const channels = await fetchApi<RoomChannel[]>(`${API}/servers/${serverId}/channels`)
      set({ channels })
      const { activeChannelId } = get()
      if (activeChannelId && channels.some((c) => c.id === activeChannelId)) {
        const channel = channels.find((c) => c.id === activeChannelId)
        if (channel?.type === 'forum') {
          get().fetchForumPosts(activeChannelId)
          get().fetchForumTags(activeChannelId)
        } else {
          get().fetchMessages(activeChannelId)
        }
        get().fetchThreads(activeChannelId)
        get().fetchDexSettings(activeChannelId)
        get().fetchArtifacts(activeChannelId)
      } else if (channels.length > 0) {
        const sorted = [...channels].sort((a, b) => a.sort_order - b.sort_order)
        get().setActiveChannel(sorted[0].id)
      } else if (activeChannelId) {
        set({ activeChannelId: null })
        saveLastActive(serverId, null)
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch channels' })
    }
  },

  createChannel: async (serverId, categoryId, name, type) => {
    try {
      const ch = await fetchApi<RoomChannel>(`${API}/servers/${serverId}/channels`, {
        method: 'POST',
        body: JSON.stringify({ category_id: categoryId, name, type }),
      })
      set((s) => ({ channels: [...s.channels, ch] }))
      return ch
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to create channel' })
      return null
    }
  },

  updateChannel: async (id, updates) => {
    try {
      const ch = await fetchApi<RoomChannel>(`${API}/channels/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })
      set((s) => ({ channels: s.channels.map((c) => (c.id === id ? ch : c)) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to update channel' })
    }
  },

  deleteChannel: async (id) => {
    try {
      await fetchApi(`${API}/channels/${id}`, { method: 'DELETE' })
      set((s) => ({
        channels: s.channels.filter((c) => c.id !== id),
        activeChannelId: s.activeChannelId === id ? null : s.activeChannelId,
      }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to delete channel' })
    }
  },

  setActiveChannel: (id) => {
    set({ activeChannelId: id, messages: [], hasMoreMessages: true, threads: [], forumPosts: [] })
    saveLastActive(get().activeServerId, id)
    if (id) {
      const channel = get().channels.find((c) => c.id === id)
      if (channel?.type === 'forum') {
        get().fetchForumPosts(id)
        get().fetchForumTags(id)
      } else {
        get().fetchMessages(id)
      }
      get().fetchThreads(id)
      get().fetchDexSettings(id)
      get().fetchArtifacts(id)
    }
  },

  // ── Message actions ──

  fetchMessages: async (channelId, before) => {
    set({ messagesLoading: true })
    try {
      const params = new URLSearchParams({ limit: '50' })
      if (before) params.set('before', before)
      const msgs = await fetchApi<RoomMessage[]>(`${API}/channels/${channelId}/messages?${params}`)
      set((s) => {
        const existingIds = new Set(s.messages.map((m) => m.id))
        const newMsgs = msgs.filter((m) => !existingIds.has(m.id))
        return {
          messages: before ? [...newMsgs, ...s.messages] : msgs,
          messagesLoading: false,
          hasMoreMessages: msgs.length === 50,
        }
      })
    } catch (e) {
      set({ messagesLoading: false, error: e instanceof Error ? e.message : 'Failed to fetch messages' })
    }
  },

  sendMessage: async (channelId, content, replyToId) => {
    const optimisticId = `opt-${Date.now()}`
    const optimistic: RoomMessage = {
      id: optimisticId,
      channel_id: channelId,
      author_id: 'operator',
      author_name: 'Operator',
      content,
      created_at: new Date().toISOString(),
      updated_at: null,
      edited: false,
      pinned: false,
      reply_to_id: replyToId ?? null,
      reply_preview: null,
      thread_id: null,
      attachments: [],
      reactions: [],
      mentions: [],
      deleted: false,
    }
    set((s) => ({ messages: [...s.messages, optimistic] }))

    try {
      const msg = await fetchApi<RoomMessage>(`${API}/channels/${channelId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content, reply_to_id: replyToId }),
      })
      set((s) => ({ messages: s.messages.map((m) => (m.id === optimisticId ? msg : m)) }))
      return msg
    } catch (e) {
      set((s) => ({
        messages: s.messages.filter((m) => m.id !== optimisticId),
        error: e instanceof Error ? e.message : 'Failed to send message',
      }))
      return null
    }
  },

  editMessage: async (id, content) => {
    try {
      const msg = await fetchApi<RoomMessage>(`${API}/messages/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ content }),
      })
      set((s) => ({ messages: s.messages.map((m) => (m.id === id ? msg : m)) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to edit message' })
    }
  },

  deleteMessage: async (id) => {
    try {
      await fetchApi(`${API}/messages/${id}`, { method: 'DELETE' })
      set((s) => ({ messages: s.messages.map((m) => (m.id === id ? { ...m, deleted: true, content: '' } : m)) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to delete message' })
    }
  },

  pinMessage: async (id, pinned) => {
    try {
      await fetchApi(`${API}/messages/${id}/pin`, {
        method: 'POST',
        body: JSON.stringify({ pinned }),
      })
      set((s) => ({ messages: s.messages.map((m) => (m.id === id ? { ...m, pinned } : m)) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to pin message' })
    }
  },

  addReaction: async (messageId, emoji) => {
    try {
      await fetchApi(`${API}/messages/${messageId}/reactions`, {
        method: 'POST',
        body: JSON.stringify({ emoji }),
      })
      set((s) => ({
        messages: s.messages.map((m) => {
          if (m.id !== messageId) return m
          const existing = m.reactions.find((r) => r.emoji === emoji)
          if (existing) {
            return { ...m, reactions: m.reactions.map((r) => r.emoji === emoji ? { ...r, count: r.count + 1, me: true } : r) }
          }
          return { ...m, reactions: [...m.reactions, { emoji, count: 1, users: ['operator'], me: true }] }
        }),
      }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to add reaction' })
    }
  },

  removeReaction: async (messageId, emoji) => {
    try {
      await fetchApi(`${API}/messages/${messageId}/reactions/${encodeURIComponent(emoji)}`, { method: 'DELETE' })
      set((s) => ({
        messages: s.messages.map((m) => {
          if (m.id !== messageId) return m
          return {
            ...m,
            reactions: m.reactions
              .map((r) => r.emoji === emoji ? { ...r, count: r.count - 1, me: false } : r)
              .filter((r) => r.count > 0),
          }
        }),
      }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to remove reaction' })
    }
  },

  // ── Thread actions ──

  fetchThreads: async (channelId) => {
    try {
      const threads = await fetchApi<RoomThread[]>(`${API}/channels/${channelId}/threads`)
      set({ threads })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch threads' })
    }
  },

  createThread: async (channelId, name, parentMessageId) => {
    try {
      const thread = await fetchApi<RoomThread>(`${API}/channels/${channelId}/threads`, {
        method: 'POST',
        body: JSON.stringify({ name, parent_message_id: parentMessageId }),
      })
      set((s) => ({ threads: [...s.threads, thread] }))
      return thread
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to create thread' })
      return null
    }
  },

  updateThread: async (id, updates) => {
    try {
      const thread = await fetchApi<RoomThread>(`${API}/threads/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })
      set((s) => ({ threads: s.threads.map((t) => (t.id === id ? thread : t)) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to update thread' })
    }
  },

  // ── Forum actions ──

  fetchForumPosts: async (channelId) => {
    try {
      const posts = await fetchApi<ForumPost[]>(`${API}/channels/${channelId}/forum/posts`)
      set({ forumPosts: posts })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch forum posts' })
    }
  },

  createForumPost: async (channelId, title, body, tags) => {
    try {
      const post = await fetchApi<ForumPost>(`${API}/channels/${channelId}/forum/posts`, {
        method: 'POST',
        body: JSON.stringify({ title, body, tags }),
      })
      set((s) => ({ forumPosts: [...s.forumPosts, post] }))
      return post
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to create forum post' })
      return null
    }
  },

  updateForumPost: async (id, updates) => {
    try {
      const post = await fetchApi<ForumPost>(`${API}/forum/posts/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })
      set((s) => ({ forumPosts: s.forumPosts.map((p) => (p.id === id ? post : p)) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to update forum post' })
    }
  },

  fetchForumTags: async (channelId) => {
    try {
      const tags = await fetchApi<ForumTag[]>(`${API}/channels/${channelId}/forum/tags`)
      set({ forumTags: tags })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch forum tags' })
    }
  },

  createForumTag: async (channelId, name, color) => {
    try {
      const tag = await fetchApi<ForumTag>(`${API}/channels/${channelId}/forum/tags`, {
        method: 'POST',
        body: JSON.stringify({ name, color }),
      })
      set((s) => ({ forumTags: [...s.forumTags, tag] }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to create forum tag' })
    }
  },

  // ── Role actions ──

  fetchRoles: async (serverId) => {
    try {
      const roles = await fetchApi<RoomRole[]>(`${API}/servers/${serverId}/roles`)
      set({ roles })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch roles' })
    }
  },

  createRole: async (serverId, name, color, permissions) => {
    try {
      const role = await fetchApi<RoomRole>(`${API}/servers/${serverId}/roles`, {
        method: 'POST',
        body: JSON.stringify({ name, color, permissions }),
      })
      set((s) => ({ roles: [...s.roles, role] }))
      return role
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to create role' })
      return null
    }
  },

  updateRole: async (id, updates) => {
    try {
      const role = await fetchApi<RoomRole>(`${API}/roles/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })
      set((s) => ({ roles: s.roles.map((r) => (r.id === id ? role : r)) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to update role' })
    }
  },

  deleteRole: async (id) => {
    try {
      await fetchApi(`${API}/roles/${id}`, { method: 'DELETE' })
      set((s) => ({ roles: s.roles.filter((r) => r.id !== id) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to delete role' })
    }
  },

  // ── Member actions ──

  fetchMembers: async (serverId) => {
    try {
      const members = await fetchApi<RoomMember[]>(`${API}/servers/${serverId}/members`)
      set({ members })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch members' })
    }
  },

  assignRole: async (serverId, userId, roleId) => {
    try {
      await fetchApi(`${API}/servers/${serverId}/members/${userId}/roles`, {
        method: 'POST',
        body: JSON.stringify({ role_id: roleId }),
      })
      set((s) => ({
        members: s.members.map((m) =>
          m.user_id === userId ? { ...m, roles: [...m.roles, roleId] } : m,
        ),
      }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to assign role' })
    }
  },

  removeRole: async (serverId, userId, roleId) => {
    try {
      await fetchApi(`${API}/servers/${serverId}/members/${userId}/roles/${roleId}`, { method: 'DELETE' })
      set((s) => ({
        members: s.members.map((m) =>
          m.user_id === userId ? { ...m, roles: m.roles.filter((r) => r !== roleId) } : m,
        ),
      }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to remove role' })
    }
  },

  updatePresence: async (status) => {
    try {
      await fetchApi(`${API}/presence`, {
        method: 'POST',
        body: JSON.stringify({ status }),
      })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to update presence' })
    }
  },

  // ── Invite actions ──

  fetchInvites: async (serverId) => {
    try {
      const invites = await fetchApi<RoomInvite[]>(`${API}/servers/${serverId}/invites`)
      set({ invites })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch invites' })
    }
  },

  createInvite: async (serverId, opts) => {
    try {
      const invite = await fetchApi<RoomInvite>(`${API}/servers/${serverId}/invites`, {
        method: 'POST',
        body: JSON.stringify({
          channel_id: opts.channel_id,
          room_type: opts.room_type,
          label: opts.label ?? null,
          max_uses: opts.max_uses ?? null,
          expires_hours: opts.expires_hours ?? null,
          allowed_email_domains: opts.allowed_email_domains ?? null,
          allowed_emails: opts.allowed_emails ?? null,
          permissions: { ...DEFAULT_GUEST_PERMISSIONS, ...opts.permissions },
        }),
      })
      set((s) => ({ invites: [...s.invites, invite] }))
      return invite
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to create invite' })
      return null
    }
  },

  revokeInvite: async (id) => {
    try {
      await fetchApi(`${API}/invites/${id}`, { method: 'DELETE' })
      set((s) => ({ invites: s.invites.map((inv) => (inv.id === id ? { ...inv, revoked: true } : inv)) }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to revoke invite' })
    }
  },

  // ── Meeting actions ──

  fetchMeeting: async (channelId) => {
    try {
      const meeting = await fetchApi<MeetingState>(`${API}/channels/${channelId}/meeting`)
      set((s) => ({ meetingStates: { ...s.meetingStates, [channelId]: meeting } }))
    } catch {
      // No meeting state yet — fine
    }
  },

  updateMeeting: async (channelId, updates) => {
    try {
      const meeting = await fetchApi<MeetingState>(`${API}/channels/${channelId}/meeting`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })
      set((s) => ({ meetingStates: { ...s.meetingStates, [channelId]: meeting } }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to update meeting' })
    }
  },

  addMeetingActionItem: async (channelId, item) => {
    try {
      const meeting = await fetchApi<MeetingState>(`${API}/channels/${channelId}/meeting/actions`, {
        method: 'POST',
        body: JSON.stringify(item),
      })
      set((s) => ({ meetingStates: { ...s.meetingStates, [channelId]: meeting } }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to add action item' })
    }
  },

  toggleMeetingActionItem: async (channelId, itemId) => {
    try {
      const meeting = await fetchApi<MeetingState>(`${API}/channels/${channelId}/meeting/actions/${itemId}/toggle`, {
        method: 'POST',
      })
      set((s) => ({ meetingStates: { ...s.meetingStates, [channelId]: meeting } }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to toggle action item' })
    }
  },

  endMeeting: async (channelId) => {
    try {
      await fetchApi(`${API}/channels/${channelId}/meeting/end`, { method: 'POST' })
      set((s) => {
        const meeting = s.meetingStates[channelId]
        if (!meeting) return s
        return {
          meetingStates: {
            ...s.meetingStates,
            [channelId]: { ...meeting, ended_at: new Date().toISOString() },
          },
        }
      })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to end meeting' })
    }
  },

  // ── Voice actions ──

  fetchVoiceState: async (channelId) => {
    try {
      const state = await fetchApi<VoiceRoomState>(`${API}/channels/${channelId}/voice`)
      set((s) => ({ voiceStates: { ...s.voiceStates, [channelId]: state } }))
    } catch {
      // No voice state yet
    }
  },

  joinVoice: async (channelId) => {
    try {
      const state = await fetchApi<VoiceRoomState>(`${API}/channels/${channelId}/voice/join`, { method: 'POST' })
      set((s) => ({ voiceStates: { ...s.voiceStates, [channelId]: state } }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to join voice room' })
    }
  },

  leaveVoice: async (channelId) => {
    try {
      await fetchApi(`${API}/channels/${channelId}/voice/leave`, { method: 'POST' })
      set((s) => {
        const next = { ...s.voiceStates }
        delete next[channelId]
        return { voiceStates: next }
      })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to leave voice room' })
    }
  },

  // ── assistant actions ──

  fetchDexSettings: async (channelId) => {
    try {
      const settings = await fetchApi<DexRoomSettings>(`${API}/channels/${channelId}/dex`)
      set((s) => ({ dexSettings: { ...s.dexSettings, [channelId]: settings } }))
    } catch {
      // Defaults apply
    }
  },

  updateDexSettings: async (channelId, updates) => {
    try {
      const settings = await fetchApi<DexRoomSettings>(`${API}/channels/${channelId}/dex`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })
      set((s) => ({ dexSettings: { ...s.dexSettings, [channelId]: settings } }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : `Failed to update ${useConfigStore.getState().aiName} settings` })
    }
  },

  dexSummarize: async (channelId) => {
    try {
      const result = await fetchApi<{ summary: string }>(`${API}/channels/${channelId}/dex/summarize`, { method: 'POST' })
      return result.summary
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to summarize' })
      return 'Summarization failed'
    }
  },

  // ── Audit log ──

  fetchAuditLog: async (serverId) => {
    try {
      const log = await fetchApi<RoomEvent[]>(`${API}/servers/${serverId}/audit-log`)
      set({ auditLog: log })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch audit log' })
    }
  },

  // ── Artifacts ──

  fetchArtifacts: async (channelId) => {
    try {
      const artifacts = await fetchApi<RoomArtifact[]>(`${API}/channels/${channelId}/artifacts`)
      set({ artifacts })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch artifacts' })
    }
  },

  createArtifact: async (channelId, name, type, metadata) => {
    try {
      const artifact = await fetchApi<RoomArtifact>(`${API}/channels/${channelId}/artifacts`, {
        method: 'POST',
        body: JSON.stringify({ name, type, metadata }),
      })
      set((s) => ({ artifacts: [...s.artifacts, artifact] }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to create artifact' })
    }
  },

  // ── Search ──

  search: async (serverId, query, filters) => {
    try {
      const params = new URLSearchParams({ q: query, ...filters })
      const results = await fetchApi<RoomSearchResult[]>(`${API}/servers/${serverId}/search?${params}`)
      set({ searchResults: results })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to search' })
    }
  },

  // ── Realtime ──

  handleWsEvent: (event) => {
    const { type, payload } = event as { type: string; payload: Record<string, unknown> }
    switch (type) {
      case 'message.created': {
        const { message: msg } = payload as { message: RoomMessage }
        if (!msg) break
        set((s) => {
          if (msg.channel_id !== s.activeChannelId) return s
          if (s.messages.some((m) => m.id === msg.id)) return s
          return { messages: [...s.messages, msg] }
        })
        break
      }
      case 'message.updated': {
        const { message: msg } = payload as { message: RoomMessage }
        if (!msg) break
        set((s) => ({ messages: s.messages.map((m) => (m.id === msg.id ? msg : m)) }))
        break
      }
      case 'message.deleted': {
        const { message_id } = payload as { message_id: string }
        set((s) => ({ messages: s.messages.map((m) => (m.id === message_id ? { ...m, deleted: true, content: '' } : m)) }))
        break
      }
      case 'channel.created': {
        const { channel } = payload as { channel: RoomChannel }
        set((s) => {
          if (channel.server_id !== s.activeServerId) return s
          if (s.channels.some((c) => c.id === channel.id)) return s
          return { channels: [...s.channels, channel] }
        })
        break
      }
      case 'channel.deleted': {
        const { channel_id } = payload as { channel_id: string }
        set((s) => ({ channels: s.channels.filter((c) => c.id !== channel_id) }))
        break
      }
      case 'member.joined': {
        const member = payload as unknown as RoomMember
        set((s) => {
          if (s.members.some((m) => m.user_id === member.user_id)) return s
          return { members: [...s.members, member] }
        })
        break
      }
      case 'presence.updated': {
        const { user_id, status, channel_id } = payload as { user_id: string; status: PresenceStatus; channel_id?: string }
        set((s) => ({
          members: s.members.map((m) =>
            m.user_id === user_id
              ? { ...m, presence: status, current_channel_id: channel_id ?? m.current_channel_id }
              : m,
          ),
        }))
        break
      }
      case 'typing.started': {
        const { user_id, channel_id } = payload as { user_id: string; channel_id: string }
        set((s) => {
          const current = s.typingUsers[channel_id] || []
          if (current.includes(user_id)) return s
          return { typingUsers: { ...s.typingUsers, [channel_id]: [...current, user_id] } }
        })
        break
      }
      case 'typing.stopped': {
        const { user_id, channel_id } = payload as { user_id: string; channel_id: string }
        set((s) => ({
          typingUsers: { ...s.typingUsers, [channel_id]: (s.typingUsers[channel_id] || []).filter((u) => u !== user_id) },
        }))
        break
      }
    }
  },

  setTyping: (channelId, userId, typing) => {
    set((s) => {
      const current = s.typingUsers[channelId] || []
      if (typing && !current.includes(userId)) {
        return { typingUsers: { ...s.typingUsers, [channelId]: [...current, userId] } }
      }
      if (!typing) {
        return { typingUsers: { ...s.typingUsers, [channelId]: current.filter((u) => u !== userId) } }
      }
      return s
    })
  },
}))
