import { useEffect, useRef, useState, type FormEvent } from 'react'
import { MessageSquare, Send, Reply, X } from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import type { RoomMessage } from '../../types/rooms'

export function RoomChatPanel() {
  const activeChannelId = useRoomsStore((s) => s.activeChannelId)
  const messages = useRoomsStore((s) => s.messages)
  const fetchMessages = useRoomsStore((s) => s.fetchMessages)
  const sendMessage = useRoomsStore((s) => s.sendMessage)
  const typingUsers = useRoomsStore((s) => s.typingUsers)

  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [replyTo, setReplyTo] = useState<RoomMessage | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (activeChannelId) fetchMessages(activeChannelId)
  }, [activeChannelId, fetchMessages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const handleSend = async (e: FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending || !activeChannelId) return
    setSending(true)
    setInput('')
    await sendMessage(activeChannelId, text, replyTo?.id)
    setReplyTo(null)
    setSending(false)
  }

  if (!activeChannelId) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          Select a channel
        </p>
      </div>
    )
  }

  const channelMessages = messages.filter((m) => m.channel_id === activeChannelId)
  const typing = typingUsers[activeChannelId] || []

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center px-3 h-8 border-b shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <MessageSquare size={11} style={{ color: 'var(--color-text-tertiary)' }} />
        <span className="text-[10px] font-mono ml-1.5" style={{ color: 'var(--color-text-secondary)' }}>
          Chat
        </span>
      </div>

      <div className="flex-1 overflow-y-auto overscroll-contain">
        {channelMessages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              No messages yet
            </p>
          </div>
        )}
        {channelMessages.map((msg) => (
          <ChatMessage
            key={msg.id}
            message={msg}
            allMessages={channelMessages}
            onReply={() => setReplyTo(msg)}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {typing.length > 0 && (
        <div className="px-3 py-0.5">
          <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            {typing.join(', ')} typing...
          </span>
        </div>
      )}

      {replyTo && (
        <div className="flex items-center gap-2 px-3 py-1 border-t"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-raised)' }}
        >
          <Reply size={10} style={{ color: 'var(--color-cyan)' }} />
          <span className="text-[9px] font-mono truncate flex-1" style={{ color: 'var(--color-text-secondary)' }}>
            Replying to <span style={{ color: 'var(--color-cyan)' }}>{replyTo.author_name}</span>
          </span>
          <button onClick={() => setReplyTo(null)} className="p-0.5">
            <X size={10} style={{ color: 'var(--color-text-tertiary)' }} />
          </button>
        </div>
      )}

      <form onSubmit={handleSend}
        className="flex items-center gap-1.5 px-2 py-1.5 border-t shrink-0"
        style={{
          borderColor: 'var(--color-border)',
          paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 6px)',
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={replyTo ? `Reply to ${replyTo.author_name}...` : 'Message...'}
          disabled={sending}
          className="flex-1 text-[10px] font-mono px-2 py-1.5 rounded border bg-transparent outline-none"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
        />
        <button type="submit"
          disabled={!input.trim() || sending}
          className="p-1.5 rounded transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center"
          style={{
            background: input.trim() ? 'var(--color-cyan)' : 'transparent',
            color: input.trim() ? 'var(--color-canvas)' : 'var(--color-text-tertiary)',
          }}
        >
          <Send size={11} />
        </button>
      </form>
    </div>
  )
}

function ChatMessage({ message: msg, allMessages, onReply }: {
  message: RoomMessage
  allMessages: RoomMessage[]
  onReply: () => void
}) {
  if (msg.deleted) return null

  const parentMsg = msg.reply_to_id
    ? allMessages.find((m) => m.id === msg.reply_to_id)
    : null

  return (
    <div className="group px-3 py-1 hover:bg-surface-raised transition-colors">
      {parentMsg && (
        <div className="flex items-center gap-1.5 mb-0.5 pl-2 border-l-2"
          style={{ borderColor: 'var(--color-cyan-dim, var(--color-border))' }}
        >
          <Reply size={8} style={{ color: 'var(--color-text-tertiary)' }} />
          <span className="text-[8px] font-mono" style={{ color: 'var(--color-cyan)' }}>
            {parentMsg.author_name}
          </span>
          <span className="text-[8px] font-mono truncate" style={{ color: 'var(--color-text-tertiary)' }}>
            {msg.reply_preview || parentMsg.content.slice(0, 60)}
          </span>
        </div>
      )}
      <div className="flex items-baseline gap-1.5">
        <span className="text-[9px] font-mono font-semibold" style={{ color: 'var(--color-cyan)' }}>
          {msg.author_name}
        </span>
        <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
        <button
          onClick={onReply}
          className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded"
          style={{ color: 'var(--color-text-tertiary)' }}
          title="Reply"
        >
          <Reply size={10} />
        </button>
      </div>
      <p className="text-[10px] font-mono whitespace-pre-wrap break-words" style={{ color: 'var(--color-text-primary)' }}>
        {msg.content}
      </p>
    </div>
  )
}
