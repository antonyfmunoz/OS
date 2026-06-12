import { lazy, Suspense } from 'react'
import { useRoomsStore } from '../../stores/roomsStore'
import { TextChannelView } from './TextChannelView'
import { ForumChannelView } from './ForumChannelView'
import { MeetingRoomPanel } from './MeetingRoomPanel'
import { ErrorBoundary } from '../ErrorBoundary'

const VoiceRoomPanel = lazy(() =>
  import('./VoiceRoomPanel').then((m) => ({ default: m.VoiceRoomPanel }))
)

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

  const isVoiceType = channel.type === 'voice' || channel.type === 'stage' || channel.type === 'broadcast'

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <RoomHeader channel={channel} />
      <div className="flex-1 min-h-0">
        <ErrorBoundary>
          {channel.type === 'forum' && <ForumChannelView channelId={channel.id} />}
          {isVoiceType && (
            <Suspense fallback={<LoadingFallback label="Loading voice..." />}>
              <VoiceRoomPanel channelId={channel.id} />
            </Suspense>
          )}
          {channel.type === 'video_meeting' && <MeetingRoomPanel channelId={channel.id} />}
          {(channel.type === 'text' || channel.type === 'announcement' || channel.type === 'files' || channel.type === 'tasks' || channel.type === 'ai_room' || channel.type === 'security') && (
            <TextChannelView channelId={channel.id} />
          )}
        </ErrorBoundary>
      </div>
    </div>
  )
}

function LoadingFallback({ label }: { label: string }) {
  return (
    <div className="flex-1 flex items-center justify-center h-full">
      <p className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>{label}</p>
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
