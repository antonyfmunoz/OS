import { useEffect, useRef } from 'react'

interface CommsMessage {
  id: string
  channel: string
  from_agent: string
  content: string
  timestamp: string
  direction: 'inbound' | 'outbound' | 'internal'
}

interface ChannelViewProps {
  channel: string
  messages: CommsMessage[]
}

function formatTime(ts: string): string {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export function ChannelView({ channel, messages }: ChannelViewProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  return (
    <div className="flex flex-col h-full">
      <div
        className="flex items-center justify-between px-4 py-2"
        style={{ borderBottom: '1px solid var(--color-border)' }}
      >
        <span className="text-xs font-medium" style={{ color: 'var(--color-text-primary)' }}>
          {channel}
        </span>
        <span className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
          {messages.length} messages
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>No messages in this channel</p>
          </div>
        )}
        {messages.map((m) => {
          const isSelf = m.direction === 'outbound'
          return (
            <div key={m.id} className={`flex flex-col ${isSelf ? 'items-end' : 'items-start'}`}>
              <div className="flex items-center gap-1 mb-0.5">
                <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>
                  {m.from_agent || 'system'}
                </span>
                <span className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
                  {formatTime(m.timestamp)}
                </span>
              </div>
              <div className={isSelf ? 'wv-bubble-self' : 'wv-bubble-other'}>
                <p className="text-xs leading-relaxed break-words">{m.content}</p>
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
