import { useEffect, useRef, useState, useCallback, type FormEvent } from 'react'
import { CornerDownLeft, Pencil, Trash2, Pin, Reply, SmilePlus } from 'lucide-react'
import { clsx } from 'clsx'
import { useRoomsStore } from '../../stores/roomsStore'
import type { RoomMessage } from '../../types/rooms'

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  const today = new Date()
  if (d.toDateString() === today.toDateString()) return 'Today'
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
}

interface MessageGroupProps {
  messages: RoomMessage[]
  onReply: (id: string) => void
}

function MessageGroup({ messages, onReply }: MessageGroupProps) {
  const editMessage = useRoomsStore((s) => s.editMessage)
  const deleteMessage = useRoomsStore((s) => s.deleteMessage)
  const pinMessage = useRoomsStore((s) => s.pinMessage)
  const addReaction = useRoomsStore((s) => s.addReaction)
  const removeReaction = useRoomsStore((s) => s.removeReaction)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const first = messages[0]
  if (!first) return null

  const handleEditSubmit = async (id: string) => {
    if (editContent.trim()) {
      await editMessage(id, editContent.trim())
    }
    setEditingId(null)
  }

  return (
    <div className="px-4 py-1 hover:bg-surface-raised transition-colors group">
      <div className="flex items-start gap-3">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-mono font-bold shrink-0 mt-0.5"
          style={{ background: 'var(--color-surface-overlay)', color: 'var(--color-cyan)' }}
        >
          {first.author_name.charAt(0).toUpperCase()}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-[11px] font-mono font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              {first.author_name}
            </span>
            <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              {formatTime(first.created_at)}
            </span>
            {first.edited && (
              <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>(edited)</span>
            )}
          </div>

          {messages.map((msg) => (
            <div
              key={msg.id}
              className="relative"
              onMouseEnter={() => setHoveredId(msg.id)}
              onMouseLeave={() => setHoveredId(null)}
            >
              {msg.deleted ? (
                <p className="text-xs font-mono italic" style={{ color: 'var(--color-text-tertiary)' }}>
                  Message deleted
                </p>
              ) : msg.reply_to_id && msg.reply_preview ? (
                <div className="mb-0.5">
                  <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
                    ↳ {msg.reply_preview}
                  </span>
                </div>
              ) : null}

              {!msg.deleted && (
                <>
                  {editingId === msg.id ? (
                    <div className="flex items-center gap-2">
                      <input
                        autoFocus
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleEditSubmit(msg.id)
                          if (e.key === 'Escape') setEditingId(null)
                        }}
                        className="flex-1 text-xs font-mono px-2 py-1 rounded border bg-transparent outline-none"
                        style={{ borderColor: 'var(--color-cyan)', color: 'var(--color-text-primary)' }}
                      />
                      <button
                        onClick={() => handleEditSubmit(msg.id)}
                        className="text-[9px] font-mono px-2 py-1 rounded"
                        style={{ background: 'var(--color-cyan)', color: 'var(--color-canvas)' }}
                      >
                        Save
                      </button>
                    </div>
                  ) : (
                    <p className="text-xs font-mono whitespace-pre-wrap break-words" style={{ color: 'var(--color-text-primary)' }}>
                      {msg.content}
                    </p>
                  )}

                  {msg.reactions.length > 0 && (
                    <div className="flex gap-1 mt-1">
                      {msg.reactions.map((r) => (
                        <button
                          key={r.emoji}
                          onClick={() => r.me ? removeReaction(msg.id, r.emoji) : addReaction(msg.id, r.emoji)}
                          className="text-[10px] px-1.5 py-0.5 rounded border transition-colors"
                          style={{
                            borderColor: r.me ? 'var(--color-cyan)' : 'var(--color-border)',
                            background: r.me ? 'var(--color-cyan-glow)' : 'transparent',
                          }}
                        >
                          {r.emoji} {r.count}
                        </button>
                      ))}
                    </div>
                  )}

                  {hoveredId === msg.id && !editingId && (
                    <div
                      className="absolute -top-3 right-0 flex items-center gap-0.5 px-1 py-0.5 rounded border"
                      style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
                    >
                      <button
                        onClick={() => onReply(msg.id)}
                        className="p-1 transition-colors"
                        style={{ color: 'var(--color-text-tertiary)' }}
                        title="Reply"
                      >
                        <Reply size={11} />
                      </button>
                      <button
                        onClick={() => addReaction(msg.id, '👍')}
                        className="p-1 transition-colors"
                        style={{ color: 'var(--color-text-tertiary)' }}
                        title="React"
                      >
                        <SmilePlus size={11} />
                      </button>
                      {msg.author_id === 'operator' && (
                        <button
                          onClick={() => { setEditingId(msg.id); setEditContent(msg.content) }}
                          className="p-1 transition-colors"
                          style={{ color: 'var(--color-text-tertiary)' }}
                          title="Edit"
                        >
                          <Pencil size={11} />
                        </button>
                      )}
                      <button
                        onClick={() => pinMessage(msg.id, !msg.pinned)}
                        className="p-1 transition-colors"
                        style={{ color: msg.pinned ? 'var(--color-cyan)' : 'var(--color-text-tertiary)' }}
                        title={msg.pinned ? 'Unpin' : 'Pin'}
                      >
                        <Pin size={11} />
                      </button>
                      {(msg.author_id === 'operator') && (
                        <button
                          onClick={() => deleteMessage(msg.id)}
                          className="p-1 transition-colors"
                          style={{ color: 'var(--color-danger)' }}
                          title="Delete"
                        >
                          <Trash2 size={11} />
                        </button>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function TextChannelView({ channelId }: { channelId: string }) {
  const messages = useRoomsStore((s) => s.messages)
  const fetchMessages = useRoomsStore((s) => s.fetchMessages)
  const sendMessage = useRoomsStore((s) => s.sendMessage)
  const messagesLoading = useRoomsStore((s) => s.messagesLoading)
  const hasMoreMessages = useRoomsStore((s) => s.hasMoreMessages)
  const typingUsers = useRoomsStore((s) => s.typingUsers)

  const [input, setInput] = useState('')
  const [replyToId, setReplyToId] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchMessages(channelId)
  }, [channelId, fetchMessages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const handleSend = async (e: FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending) return
    setSending(true)
    setInput('')
    await sendMessage(channelId, text, replyToId ?? undefined)
    setReplyToId(null)
    setSending(false)
  }

  const handleScroll = useCallback(() => {
    if (!scrollRef.current || messagesLoading || !hasMoreMessages) return
    if (scrollRef.current.scrollTop < 100 && messages.length > 0) {
      fetchMessages(channelId, messages[0].id)
    }
  }, [channelId, fetchMessages, messages, messagesLoading, hasMoreMessages])

  const grouped = groupMessages(messages.filter((m) => m.channel_id === channelId))
  const typing = typingUsers[channelId] || []

  const replyMsg = replyToId ? messages.find((m) => m.id === replyToId) : null

  return (
    <div className="flex flex-col h-full">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto"
      >
        {messagesLoading && messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>Loading messages...</p>
          </div>
        )}

        {!messagesLoading && messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-xs font-mono" style={{ color: 'var(--color-text-secondary)' }}>
                No messages yet
              </p>
              <p className="text-[10px] font-mono mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
                Start the conversation
              </p>
            </div>
          </div>
        )}

        {grouped.map((group, i) => (
          <div key={group.key}>
            {group.dateSep && (
              <div className="flex items-center px-4 py-2 gap-2">
                <div className="flex-1 h-px" style={{ background: 'var(--color-border)' }} />
                <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
                  {group.dateSep}
                </span>
                <div className="flex-1 h-px" style={{ background: 'var(--color-border)' }} />
              </div>
            )}
            <MessageGroup messages={group.messages} onReply={setReplyToId} />
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      {typing.length > 0 && (
        <div className="px-4 py-0.5">
          <span className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            {typing.join(', ')} {typing.length === 1 ? 'is' : 'are'} typing...
          </span>
        </div>
      )}

      {replyMsg && (
        <div
          className="flex items-center gap-2 px-4 py-1 border-t"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-raised)' }}
        >
          <Reply size={10} style={{ color: 'var(--color-cyan)' }} />
          <span className="text-[9px] font-mono truncate" style={{ color: 'var(--color-text-secondary)' }}>
            Replying to {replyMsg.author_name}: {replyMsg.content.slice(0, 60)}
          </span>
          <button
            onClick={() => setReplyToId(null)}
            className="ml-auto text-[9px] font-mono"
            style={{ color: 'var(--color-text-tertiary)' }}
          >
            Cancel
          </button>
        </div>
      )}

      <form
        onSubmit={handleSend}
        className="flex items-center gap-2 px-4 py-2 border-t shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Send a message..."
          disabled={sending}
          className="flex-1 text-xs font-mono px-3 py-2 rounded border bg-transparent outline-none"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
        />
        <button
          type="submit"
          disabled={!input.trim() || sending}
          className="flex items-center gap-1 text-xs font-mono px-3 py-2 rounded transition-colors"
          style={{
            background: input.trim() ? 'var(--color-cyan)' : 'var(--color-surface-raised)',
            color: input.trim() ? 'var(--color-canvas)' : 'var(--color-text-tertiary)',
            cursor: input.trim() ? 'pointer' : 'default',
          }}
        >
          <CornerDownLeft size={12} />
        </button>
      </form>
    </div>
  )
}

interface MessageGroupData {
  key: string
  dateSep: string | null
  messages: RoomMessage[]
}

function groupMessages(messages: RoomMessage[]): MessageGroupData[] {
  const groups: MessageGroupData[] = []
  let lastDate = ''
  let currentGroup: RoomMessage[] = []
  let currentAuthor = ''

  const flush = (dateSep: string | null) => {
    if (currentGroup.length > 0) {
      groups.push({
        key: currentGroup[0].id,
        dateSep,
        messages: currentGroup,
      })
      currentGroup = []
    }
  }

  messages.forEach((msg) => {
    const msgDate = formatDate(msg.created_at)
    const dateSep = msgDate !== lastDate ? msgDate : null
    lastDate = msgDate

    if (dateSep || msg.author_id !== currentAuthor) {
      flush(dateSep)
      currentAuthor = msg.author_id
    }
    currentGroup.push(msg)
  })

  flush(null)
  return groups
}
