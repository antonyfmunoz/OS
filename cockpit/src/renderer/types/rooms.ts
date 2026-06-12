export type ChannelType =
  | 'text'
  | 'voice'
  | 'video_meeting'
  | 'forum'
  | 'stage'
  | 'broadcast'
  | 'announcement'
  | 'files'
  | 'tasks'
  | 'ai_room'
  | 'security'

export type ServerPrivacy = 'private' | 'internal' | 'client_facing' | 'community'

export type ServerTemplate =
  | 'founder_war_room'
  | 'sales_team'
  | 'client_delivery'
  | 'engineering'
  | 'creator_studio'
  | 'community'
  | 'coaching_cohort'
  | 'broadcast_studio'
  | 'security_ops'
  | 'empty'

export type PresenceStatus = 'online' | 'away' | 'busy' | 'offline'

export type MemberRole = 'owner' | 'admin' | 'moderator' | 'member' | 'guest' | 'client'

export type DexRoomMode =
  | 'founder_operator'
  | 'sales_coach'
  | 'client_success'
  | 'engineering_pm'
  | 'technical_reviewer'
  | 'meeting_notetaker'
  | 'podcast_producer'
  | 'broadcast_director'
  | 'security_analyst'
  | 'education_facilitator'
  | 'community_moderator'
  | 'disabled'

export type MeetingMode =
  | 'sales_call'
  | 'coaching_call'
  | 'investor_call'
  | 'hiring_interview'
  | 'team_meeting'
  | 'client_onboarding'
  | 'podcast_interview'
  | 'training_review'
  | 'war_room'

export type RoomPermission =
  | 'view_server'
  | 'manage_server'
  | 'manage_roles'
  | 'manage_channels'
  | 'manage_permissions'
  | 'create_invites'
  | 'view_channel'
  | 'send_messages'
  | 'manage_messages'
  | 'create_threads'
  | 'manage_threads'
  | 'attach_files'
  | 'add_reactions'
  | 'mention_everyone'
  | 'join_voice'
  | 'speak'
  | 'mute_members'
  | 'deafen_members'
  | 'move_members'
  | 'share_screen'
  | 'start_video'
  | 'record_meeting'
  | 'view_transcripts'
  | 'manage_room_memory'
  | 'manage_dex_mode'
  | 'create_work_packets'
  | 'approve_room_actions'
  | 'invite_guests'

export interface RoomServer {
  id: string
  name: string
  description: string
  icon_emoji: string
  owner_id: string
  privacy: ServerPrivacy
  template: ServerTemplate | null
  created_at: string
  updated_at: string
  archived: boolean
  sort_order: number
  pinned: boolean
}

export interface ServerCategory {
  id: string
  server_id: string
  name: string
  sort_order: number
  collapsed: boolean
  muted: boolean
  permission_synced: boolean
}

export interface RoomChannel {
  id: string
  server_id: string
  category_id: string | null
  name: string
  topic: string
  type: ChannelType
  sort_order: number
  private: boolean
  locked: boolean
  slowmode_seconds: number
  archived: boolean
  unread_count: number
  mention_count: number
  muted: boolean
  last_message_at: string | null
  dex_mode: DexRoomMode
  dex_enabled: boolean
  memory_scope: 'room' | 'server' | 'global'
}

export interface RoomMessage {
  id: string
  channel_id: string
  author_id: string
  author_name: string
  content: string
  created_at: string
  updated_at: string | null
  edited: boolean
  pinned: boolean
  reply_to_id: string | null
  reply_preview: string | null
  thread_id: string | null
  attachments: RoomAttachment[]
  reactions: RoomReaction[]
  mentions: string[]
  deleted: boolean
}

export interface RoomAttachment {
  id: string
  message_id: string
  filename: string
  content_type: string
  size_bytes: number
  url: string
}

export interface RoomReaction {
  emoji: string
  count: number
  users: string[]
  me: boolean
}

export interface RoomThread {
  id: string
  channel_id: string
  name: string
  created_by: string
  created_at: string
  message_count: number
  last_message_at: string | null
  archived: boolean
  locked: boolean
  private: boolean
  parent_message_id: string | null
}

export interface ForumPost {
  id: string
  channel_id: string
  title: string
  body: string
  author_id: string
  author_name: string
  tags: string[]
  created_at: string
  updated_at: string | null
  pinned: boolean
  locked: boolean
  closed: boolean
  reply_count: number
  last_reply_at: string | null
}

export interface ForumTag {
  id: string
  channel_id: string
  name: string
  color: string
}

export interface RoomRole {
  id: string
  server_id: string
  name: string
  color: string
  icon_emoji: string
  sort_order: number
  permissions: RoomPermission[]
  is_default: boolean
}

export interface RoomMember {
  id: string
  server_id: string
  user_id: string
  display_name: string
  roles: string[]
  joined_at: string
  presence: PresenceStatus
  current_channel_id: string | null
  last_active_at: string
  is_typing: boolean
  is_speaking: boolean
  is_muted: boolean
  is_deafened: boolean
}

export type GuestRole = 'temporary_guest'

export interface GuestPermissions {
  can_speak: boolean
  can_video: boolean
  can_screen_share: boolean
  can_chat: boolean
}

export const DEFAULT_GUEST_PERMISSIONS: GuestPermissions = {
  can_speak: true,
  can_video: true,
  can_screen_share: false,
  can_chat: true,
}

export interface RoomInvite {
  id: string
  server_id: string
  channel_id: string | null
  room_type: 'voice' | 'meeting'
  created_by: string
  code: string
  label: string | null
  max_uses: number | null
  uses: number
  expires_at: string | null
  allowed_email_domains: string[] | null
  allowed_emails: string[] | null
  guest_role: GuestRole
  permissions: GuestPermissions
  role_on_join: string | null
  created_at: string
  revoked: boolean
}

export interface MeetingState {
  id: string
  channel_id: string
  objective: string
  agenda: string[]
  participants: string[]
  notes: string
  action_items: MeetingActionItem[]
  decisions: string[]
  mode: MeetingMode
  started_at: string | null
  ended_at: string | null
  recording_consent: boolean
  ai_assistance: boolean
  transcript_placeholder: boolean
}

export interface MeetingActionItem {
  id: string
  text: string
  assignee: string
  due_date: string | null
  completed: boolean
}

export interface VoiceRoomState {
  channel_id: string
  participants: VoiceParticipant[]
  topic: string
  capacity: number
  locked: boolean
}

export interface VoiceParticipant {
  user_id: string
  display_name: string
  is_speaking: boolean
  is_muted: boolean
  is_deafened: boolean
  joined_at: string
}

export interface RoomEvent {
  id: string
  server_id: string
  channel_id: string | null
  type: string
  actor_id: string
  actor_name: string
  details: Record<string, unknown>
  created_at: string
}

export interface RoomArtifact {
  id: string
  channel_id: string
  name: string
  type: string
  owner_id: string
  pinned: boolean
  created_at: string
  metadata: Record<string, unknown>
}

export interface DexRoomSettings {
  channel_id: string
  enabled: boolean
  mode: DexRoomMode
  memory_scope: 'room' | 'server' | 'global'
  allowed_actions: string[]
  autonomy_level: 'passive' | 'suggest' | 'active' | 'autonomous'
  meeting_listener: boolean
  transcript_enabled: boolean
  recording_enabled: boolean
  action_creation: boolean
  approval_required: boolean
  summarization: boolean
}

export interface RoomSearchResult {
  type: 'message' | 'thread' | 'forum_post' | 'file' | 'member'
  id: string
  channel_id: string
  server_id: string
  title: string
  excerpt: string
  author: string
  timestamp: string
}

export type RoomWsEvent =
  | { type: 'message.created'; payload: RoomMessage }
  | { type: 'message.updated'; payload: RoomMessage }
  | { type: 'message.deleted'; payload: { id: string; channel_id: string } }
  | { type: 'reaction.added'; payload: { message_id: string; emoji: string; user_id: string } }
  | { type: 'reaction.removed'; payload: { message_id: string; emoji: string; user_id: string } }
  | { type: 'thread.created'; payload: RoomThread }
  | { type: 'thread.updated'; payload: RoomThread }
  | { type: 'channel.created'; payload: RoomChannel }
  | { type: 'channel.updated'; payload: RoomChannel }
  | { type: 'channel.deleted'; payload: { id: string; server_id: string } }
  | { type: 'member.joined'; payload: RoomMember }
  | { type: 'member.left'; payload: { user_id: string; server_id: string } }
  | { type: 'presence.updated'; payload: { user_id: string; status: PresenceStatus; channel_id?: string } }
  | { type: 'typing.started'; payload: { user_id: string; channel_id: string } }
  | { type: 'typing.stopped'; payload: { user_id: string; channel_id: string } }
  | { type: 'voice.joined'; payload: VoiceParticipant & { channel_id: string } }
  | { type: 'voice.left'; payload: { user_id: string; channel_id: string } }
  | { type: 'role.updated'; payload: RoomRole }
  | { type: 'permission.updated'; payload: { channel_id: string; role_id: string; permissions: RoomPermission[] } }
  | { type: 'invite.created'; payload: RoomInvite }
  | { type: 'audit.created'; payload: RoomEvent }
  | { type: 'room.dex.updated'; payload: DexRoomSettings }
