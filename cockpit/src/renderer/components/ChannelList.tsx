export interface Conversation {
  id: string
  label: string
  participants: string[]
  lastMessage: string
  lastSender: string
  lastTime: string
  count: number
  intent?: string
}

interface ConversationListProps {
  conversations: Conversation[]
  selected: string | null
  onSelect: (conversationId: string) => void
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

const INTENT_ICON: Record<string, string> = {
  delegate_task: '→',
  dex_response: '←',
  operator_command: '▶',
  report: '■',
}

export function ConversationList({ conversations, selected, onSelect }: ConversationListProps) {
  if (conversations.length === 0) {
    return (
      <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--color-text-tertiary)' }}>
        No conversations
      </div>
    )
  }

  return (
    <div className="overflow-y-auto h-full">
      {conversations.map((conv) => (
        <div
          key={conv.id}
          onClick={() => onSelect(conv.id)}
          className={`wv-channel-list-item ${selected === conv.id ? 'selected' : ''}`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
              {conv.participants.join(' ↔ ')}
            </span>
            <span className="text-[10px] flex-shrink-0 ml-2" style={{ color: 'var(--color-text-tertiary)' }}>
              {timeAgo(conv.lastTime)}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {conv.intent && (
              <span className="text-[10px] flex-shrink-0 font-mono" style={{ color: 'var(--color-cyan)' }}>
                {INTENT_ICON[conv.intent] || '•'}
              </span>
            )}
            <span className="text-[10px] flex-shrink-0" style={{ color: 'var(--color-text-secondary)' }}>
              {conv.lastSender}:
            </span>
            <span className="text-[10px] truncate flex-1" style={{ color: 'var(--color-text-tertiary)' }}>
              {conv.lastMessage}
            </span>
            {conv.count > 1 && (
              <span
                className="text-[9px] px-2 rounded-full flex-shrink-0 font-mono"
                style={{ background: 'var(--color-cyan-glow)', color: 'var(--color-cyan)' }}
              >
                {conv.count}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
