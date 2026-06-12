import { useEffect, useRef, useState, type FormEvent } from 'react'
import { MessageSquare, Send, Plus, Archive, Lock, ChevronDown, ChevronRight } from 'lucide-react'
import { useRoomsStore } from '../../stores/roomsStore'
import type { RoomMessage } from '../../types/rooms'

export function ThreadPanel() {
  const activeChannelId = useRoomsStore((s) => s.activeChannelId)

  if (!activeChannelId) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          Select a channel
        </p>
      </div>
    )
  }

  return <ChannelChat channelId={activeChannelId} />
}

function ChannelChat({ channelId }: { channelId: string }) {
  const messages = useRoomsStore((s) => s.messages)
  const fetchMessages = useRoomsStore((s) => s.fetchMessages)
  const sendMessage = useRoomsStore((s) => s.sendMessage)
  const typingUsers = useRoomsStore((s) => s.typingUsers)
  const threads = useRoomsStore((s) => s.threads)
  const createThread = useRoomsStore((s) => s.createThread)
  const updateThread = useRoomsStore((s) => s.updateThread)

  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [threadsExpanded, setThreadsExpanded] = useState(false)
  const [showCreateThread, setShowCreateThread] = useState(false)
  const [threadName, setThreadName] = useState('')
  const [creatingThread, setCreatingThread] = useState(false)
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
    await sendMessage(channelId, text)
    setSending(false)
  }

  const handleCreateThread = async (e: FormEvent) => {
    e.preventDefault()
    if (!threadName.trim() || creatingThread) return
    setCreatingThread(true)
    await createThread(channelId, threadName.trim())
    setThreadName('')
    setShowCreateThread(false)
    setCreatingThread(false)
  }

  const channelMessages = messages.filter((m) => m.channel_id === channelId)
  const typing = typingUsers[channelId] || []
  const activeThreads = threads.filter((t) => !t.archived)
  const archivedThreads = threads.filter((t) => t.archived)

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto overscroll-contain">
        {channelMessages.length === 0 && (
          <div className="flex items-center justify-center h-24">
            <p className="text-[9px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              No messages yet
            </p>
          </div>
        )}
        {channelMessages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {typing.length > 0 && (
        <div className="px-2 py-0.5">
          <span className="text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            {typing.join(', ')} typing...
          </span>
        </div>
      )}

      {/* Message input */}
      <form onSubmit={handleSend}
        className="flex items-center gap-1 px-2 py-1.5 border-t shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message..."
          disabled={sending}
          className="flex-1 text-[9px] font-mono px-2 py-1 rounded border bg-transparent outline-none"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
        />
        <button type="submit"
          disabled={!input.trim() || sending}
          className="p-1 rounded transition-colors min-w-[28px] min-h-[28px] flex items-center justify-center"
          style={{
            background: input.trim() ? 'var(--color-cyan)' : 'transparent',
            color: input.trim() ? 'var(--color-canvas)' : 'var(--color-text-tertiary)',
          }}
        >
          <Send size={10} />
        </button>
      </form>

      {/* Threads section — collapsible at bottom */}
      <div className="border-t shrink-0" style={{ borderColor: 'var(--color-border)' }}>
        <button
          onClick={() => setThreadsExpanded(!threadsExpanded)}
          className="w-full flex items-center gap-1.5 px-2 py-1.5 text-[9px] font-mono"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          {threadsExpanded ? <ChevronDown size={9} /> : <ChevronRight size={9} />}
          <MessageSquare size={9} />
          <span>Threads ({activeThreads.length})</span>
          <button
            onClick={(e) => { e.stopPropagation(); setShowCreateThread(!showCreateThread) }}
            className="ml-auto p-0.5"
            style={{ color: 'var(--color-text-tertiary)' }}
          >
            <Plus size={9} />
          </button>
        </button>

        {threadsExpanded && (
          <div className="px-2 pb-2 space-y-1 max-h-40 overflow-y-auto">
            {showCreateThread && (
              <form onSubmit={handleCreateThread} className="flex gap-1">
                <input
                  autoFocus
                  value={threadName}
                  onChange={(e) => setThreadName(e.target.value)}
                  placeholder="Thread name"
                  className="flex-1 text-[9px] font-mono px-2 py-1 rounded border bg-transparent outline-none"
                  style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
                />
                <button type="submit" disabled={!threadName.trim()}
                  className="text-[8px] font-mono px-2 py-1 rounded"
                  style={{ background: 'var(--color-cyan)', color: 'var(--color-canvas)' }}
                >
                  Go
                </button>
              </form>
            )}

            {activeThreads.map((thread) => (
              <div key={thread.id}
                className="flex items-center gap-1.5 py-0.5 px-1 rounded transition-colors hover:bg-surface-raised cursor-pointer"
              >
                <MessageSquare size={9} style={{ color: 'var(--color-text-tertiary)' }} />
                <div className="flex-1 min-w-0">
                  <span className="text-[9px] font-mono truncate block" style={{ color: 'var(--color-text-primary)' }}>
                    {thread.name}
                  </span>
                  <span className="text-[7px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
                    {thread.message_count} msgs
                  </span>
                </div>
                {thread.locked && <Lock size={7} style={{ color: 'var(--color-warn)' }} />}
              </div>
            ))}

            {activeThreads.length === 0 && !showCreateThread && (
              <p className="text-[8px] font-mono text-center py-1" style={{ color: 'var(--color-text-tertiary)' }}>
                No threads
              </p>
            )}

            {archivedThreads.length > 0 && (
              <div className="mt-1">
                <div className="flex items-center gap-1 mb-0.5">
                  <Archive size={8} style={{ color: 'var(--color-text-tertiary)' }} />
                  <span className="text-[7px] font-mono uppercase" style={{ color: 'var(--color-text-tertiary)' }}>
                    Archived ({archivedThreads.length})
                  </span>
                </div>
                {archivedThreads.map((thread) => (
                  <div key={thread.id} className="flex items-center gap-1.5 py-0.5 px-1">
                    <span className="text-[8px] font-mono truncate" style={{ color: 'var(--color-text-tertiary)' }}>
                      {thread.name}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function ChatMessage({ message: msg }: { message: RoomMessage }) {
  if (msg.deleted) return null
  return (
    <div className="px-2 py-1 hover:bg-surface-raised transition-colors">
      <div className="flex items-baseline gap-1">
        <span className="text-[8px] font-mono font-semibold" style={{ color: 'var(--color-cyan)' }}>
          {msg.author_name}
        </span>
        <span className="text-[7px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      <p className="text-[9px] font-mono whitespace-pre-wrap break-words" style={{ color: 'var(--color-text-primary)' }}>
        {msg.content}
      </p>
    </div>
  )
}
