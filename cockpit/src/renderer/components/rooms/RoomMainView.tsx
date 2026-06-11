import { useRoomsStore } from '../../stores/roomsStore'
import { TextChannelView } from './TextChannelView'
import { ForumChannelView } from './ForumChannelView'
import { VoiceRoomPanel } from './VoiceRoomPanel'
import { MeetingRoomPanel } from './MeetingRoomPanel'

export function RoomMainView() {
  const activeChannelId = useRoomsStore((s) => s.activeChannelId)
  const channels = useRoomsStore((s) => s.channels)
  const channel = channels.find((c) => c.id === activeChannelId)

  if (!channel) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          Select a channel
        </p>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <RoomHeader channel={channel} />
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

function RoomHeader({ channel }: { channel: { name: string; topic: string; type: string; locked: boolean } }) {
  return (
    <div
      className="flex items-center px-3 h-9 shrink-0 border-b gap-2"
      style={{ borderColor: 'var(--color-border)' }}
    >
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
    </div>
  )
}
