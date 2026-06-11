import { ChevronLeft, ChevronRight, Menu, Users } from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import { TextChannelView } from './TextChannelView'
import { ForumChannelView } from './ForumChannelView'
import { VoiceRoomPanel } from './VoiceRoomPanel'
import { MeetingRoomPanel } from './MeetingRoomPanel'

interface Props {
  channelSidebarOpen: boolean
  rightRailOpen: boolean
  onToggleChannelSidebar: () => void
  onToggleRightRail: () => void
}

export function RoomMainView({ channelSidebarOpen, rightRailOpen, onToggleChannelSidebar, onToggleRightRail }: Props) {
  const activeChannelId = useRoomsStore((s) => s.activeChannelId)
  const channels = useRoomsStore((s) => s.channels)
  const channel = channels.find((c) => c.id === activeChannelId)

  if (!channel) {
    return (
      <div className="flex-1 flex flex-col">
        <RoomToolbar
          channelSidebarOpen={channelSidebarOpen}
          rightRailOpen={rightRailOpen}
          onToggleChannelSidebar={onToggleChannelSidebar}
          onToggleRightRail={onToggleRightRail}
        />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            Select a channel
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <RoomHeader
        channel={channel}
        channelSidebarOpen={channelSidebarOpen}
        rightRailOpen={rightRailOpen}
        onToggleChannelSidebar={onToggleChannelSidebar}
        onToggleRightRail={onToggleRightRail}
      />
      <div className="flex-1 min-h-0">
        {channel.type === 'forum' && <ForumChannelView channelId={channel.id} />}
        {channel.type === 'voice' && <VoiceRoomPanel channelId={channel.id} />}
        {channel.type === 'video_meeting' && <MeetingRoomPanel channelId={channel.id} />}
        {(channel.type === 'text' || channel.type === 'announcement' || channel.type === 'files' || channel.type === 'tasks' || channel.type === 'ai_room' || channel.type === 'security') && (
          <TextChannelView channelId={channel.id} />
        )}
        {channel.type === 'stage' && <VoiceRoomPanel channelId={channel.id} />}
        {channel.type === 'broadcast' && <VoiceRoomPanel channelId={channel.id} />}
      </div>
    </div>
  )
}

function RoomToolbar({
  channelSidebarOpen,
  rightRailOpen,
  onToggleChannelSidebar,
  onToggleRightRail,
}: {
  channelSidebarOpen: boolean
  rightRailOpen: boolean
  onToggleChannelSidebar: () => void
  onToggleRightRail: () => void
}) {
  return (
    <div
      className="flex items-center px-3 h-9 shrink-0 border-b gap-2"
      style={{ borderColor: 'var(--color-border)' }}
    >
      <button
        onClick={onToggleChannelSidebar}
        className="p-1 transition-colors"
        style={{ color: channelSidebarOpen ? 'var(--color-cyan)' : 'var(--color-text-tertiary)' }}
        title={channelSidebarOpen ? 'Hide channels' : 'Show channels'}
      >
        <Menu size={14} />
      </button>
      <span className="flex-1" />
      <button
        onClick={onToggleRightRail}
        className="p-1 transition-colors"
        style={{ color: rightRailOpen ? 'var(--color-cyan)' : 'var(--color-text-tertiary)' }}
        title={rightRailOpen ? 'Hide details' : 'Show details'}
      >
        <Users size={14} />
      </button>
    </div>
  )
}

function RoomHeader({
  channel,
  channelSidebarOpen,
  rightRailOpen,
  onToggleChannelSidebar,
  onToggleRightRail,
}: {
  channel: { name: string; topic: string; type: string; locked: boolean }
  channelSidebarOpen: boolean
  rightRailOpen: boolean
  onToggleChannelSidebar: () => void
  onToggleRightRail: () => void
}) {
  return (
    <div
      className="flex items-center px-3 h-9 shrink-0 border-b gap-2"
      style={{ borderColor: 'var(--color-border)' }}
    >
      <button
        onClick={onToggleChannelSidebar}
        className="p-1 transition-colors shrink-0"
        style={{ color: channelSidebarOpen ? 'var(--color-cyan)' : 'var(--color-text-tertiary)' }}
        title={channelSidebarOpen ? 'Hide channels' : 'Show channels'}
      >
        {channelSidebarOpen ? <ChevronLeft size={14} /> : <Menu size={14} />}
      </button>

      <span className="text-[11px] font-mono font-semibold truncate" style={{ color: 'var(--color-text-primary)' }}>
        # {channel.name}
      </span>
      {channel.topic && (
        <>
          <span className="text-[10px] shrink-0" style={{ color: 'var(--color-border)' }}>|</span>
          <span className="text-[10px] font-mono truncate" style={{ color: 'var(--color-text-tertiary)' }}>
            {channel.topic}
          </span>
        </>
      )}
      {channel.locked && (
        <span className="text-[9px] font-mono px-1.5 rounded shrink-0" style={{ background: 'var(--color-warn-dim)', color: 'var(--color-warn)' }}>
          LOCKED
        </span>
      )}
      <span className="flex-1" />
      <span
        className="text-[9px] font-mono uppercase px-1.5 rounded shrink-0"
        style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-tertiary)' }}
      >
        {channel.type}
      </span>
      <button
        onClick={onToggleRightRail}
        className="p-1 transition-colors shrink-0"
        style={{ color: rightRailOpen ? 'var(--color-cyan)' : 'var(--color-text-tertiary)' }}
        title={rightRailOpen ? 'Hide details' : 'Show details'}
      >
        {rightRailOpen ? <ChevronRight size={14} /> : <Users size={14} />}
      </button>
    </div>
  )
}
