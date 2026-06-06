export interface Channel {
  name: string
  lastMessage: string
  lastFrom: string
  lastTime: string
  count: number
}

interface ChannelListProps {
  channels: Channel[]
  selected: string | null
  onSelect: (channel: string) => void
}

function timeAgo(ts: string): string {
  if (!ts) return ''
  try {
    const diff = Date.now() - new Date(ts).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'now'
    if (mins < 60) return `${mins}m`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h`
    return `${Math.floor(hrs / 24)}d`
  } catch {
    return ''
  }
}

export function ChannelList({ channels, selected, onSelect }: ChannelListProps) {
  if (channels.length === 0) {
    return (
      <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--color-text-tertiary)' }}>
        No channels
      </div>
    )
  }

  return (
    <div className="overflow-y-auto h-full">
      {channels.map((ch) => (
        <div
          key={ch.name}
          onClick={() => onSelect(ch.name)}
          className={`wv-channel-list-item ${selected === ch.name ? 'selected' : ''}`}
        >
          <div className="flex items-center justify-between mb-0.5">
            <span className="text-xs font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
              {ch.name}
            </span>
            <span className="text-[10px] flex-shrink-0 ml-2" style={{ color: 'var(--color-text-tertiary)' }}>
              {timeAgo(ch.lastTime)}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[10px] flex-shrink-0" style={{ color: 'var(--color-text-secondary)' }}>
              {ch.lastFrom}:
            </span>
            <span className="text-[10px] truncate flex-1" style={{ color: 'var(--color-text-tertiary)' }}>
              {ch.lastMessage}
            </span>
            {ch.count > 0 && (
              <span
                className="text-[9px] px-1.5 rounded-full flex-shrink-0 font-mono"
                style={{ background: 'var(--color-cyan-glow)', color: 'var(--color-cyan)' }}
              >
                {ch.count}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
