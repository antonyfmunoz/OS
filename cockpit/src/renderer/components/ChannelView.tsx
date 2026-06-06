import { useEffect, useRef } from 'react'

export interface A2AMessage {
  id: string
  sender: string
  recipient: string
  intent: string
  content: string
  payload: Record<string, unknown>
  conversation_id: string
  parent_message_id: string | null
  timestamp: string
  direction: 'inbound' | 'outbound' | 'internal'
}

interface ConversationViewProps {
  conversationId: string
  messages: A2AMessage[]
  participants: string[]
}

function formatTime(ts: string): string {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

const INTENT_LABEL: Record<string, { label: string; color: string }> = {
  delegate_task: { label: 'DELEGATE', color: 'var(--color-warn)' },
  dex_response: { label: 'RESPONSE', color: 'var(--color-ok)' },
  operator_command: { label: 'COMMAND', color: 'var(--color-cyan)' },
  report: { label: 'REPORT', color: 'var(--color-text-secondary)' },
}

export function ConversationView({ conversationId, messages, participants }: ConversationViewProps) {
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
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
            {participants.join(' ↔ ')}
          </span>
          <span
            className="text-[9px] font-mono px-2 py-1 rounded"
            style={{ color: 'var(--color-text-tertiary)', background: 'var(--color-surface-raised)' }}
          >
            {conversationId.slice(0, 8)}
          </span>
        </div>
        <span className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
          {messages.length} messages
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>No messages in this thread</p>
          </div>
        )}
        {messages.map((m) => {
          const isSelf = m.direction === 'outbound'
          const intentInfo = INTENT_LABEL[m.intent]
          return (
            <div key={m.id} className={`flex flex-col ${isSelf ? 'items-end' : 'items-start'}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>
                  {m.sender}
                </span>
                <span className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>→</span>
                <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>
                  {m.recipient}
                </span>
                {intentInfo && (
                  <span
                    className="text-[8px] font-mono uppercase px-1 rounded"
                    style={{ color: intentInfo.color, background: 'var(--color-surface-raised)' }}
                  >
                    {intentInfo.label}
                  </span>
                )}
                <span className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
                  {formatTime(m.timestamp)}
                </span>
              </div>
              <div className={isSelf ? 'wv-bubble-self' : 'wv-bubble-other'}>
                <p className="text-xs leading-relaxed break-words">{m.content}</p>
              </div>
              {m.parent_message_id && (
                <span className="text-[9px] mt-1 font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
                  reply to {m.parent_message_id.slice(0, 8)}
                </span>
              )}
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
