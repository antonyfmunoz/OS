import { useState, useEffect, useRef, useCallback, type FormEvent } from 'react'
import { fetchApi } from '../api/client'

interface CommsMessage {
  id: string
  channel: string
  from_agent: string
  content: string
  timestamp: string
  direction: 'inbound' | 'outbound' | 'internal'
}

function DirectionBadge({ direction }: { direction: string }) {
  const styles: Record<string, { color: string; bg: string; label: string }> = {
    inbound: { color: '#4ade80', bg: 'rgba(74,222,128,0.12)', label: 'IN' },
    outbound: { color: '#60a5fa', bg: 'rgba(96,165,250,0.12)', label: 'OUT' },
    internal: { color: 'var(--color-text-tertiary)', bg: 'var(--color-surface-raised)', label: 'INT' },
  }
  const s = styles[direction] || styles.internal
  return (
    <span
      className="text-[9px] font-mono px-1 rounded"
      style={{ color: s.color, background: s.bg }}
    >
      {s.label}
    </span>
  )
}

function ChannelBadge({ channel }: { channel: string }) {
  const short = channel.replace('organism/', '').slice(0, 12)
  const isDiscord = channel.includes('discord')
  return (
    <span
      className="text-[9px] font-mono px-1 rounded"
      style={{
        color: isDiscord ? '#7289da' : 'var(--color-text-tertiary)',
        background: isDiscord ? 'rgba(114,137,218,0.12)' : 'var(--color-surface-raised)',
      }}
    >
      {short}
    </span>
  )
}

function formatTime(ts: string): string {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export function CommsPanel() {
  const [messages, setMessages] = useState<CommsMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [sendText, setSendText] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const fetchMessages = useCallback(async () => {
    try {
      const data = await fetchApi<CommsMessage[]>('/comms?limit=100')
      setMessages(data)
    } catch (err) {
      console.error('comms fetch failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMessages()
    const interval = setInterval(fetchMessages, 5000)
    return () => clearInterval(interval)
  }, [fetchMessages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const handleSend = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    const text = sendText.trim()
    if (!text || sending) return
    setSending(true)
    try {
      await fetchApi('/comms/send', {
        method: 'POST',
        body: JSON.stringify({ recipient: 'system', content: text }),
      })
      setSendText('')
      await fetchMessages()
    } catch (err) {
      console.error('comms send failed:', err)
    } finally {
      setSending(false)
    }
  }, [sendText, sending, fetchMessages])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
          Messages
        </h2>
        <span className="ml-2 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
          cross-channel communications
        </span>
        <span className="ml-auto text-xs tabular-nums" style={{ color: 'var(--color-text-tertiary)' }}>
          {messages.length}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-1">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>Loading...</p>
          </div>
        )}
        {!loading && messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>No messages</p>
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className="flex items-start gap-2 py-1.5 px-2 rounded text-xs"
            style={{ background: 'var(--color-surface-raised)' }}
          >
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="font-mono font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                  {m.from_agent}
                </span>
                <DirectionBadge direction={m.direction} />
                <ChannelBadge channel={m.channel} />
                <span className="ml-auto text-[10px] tabular-nums" style={{ color: 'var(--color-text-tertiary)' }}>
                  {formatTime(m.timestamp)}
                </span>
              </div>
              <p className="text-xs leading-relaxed break-words" style={{ color: 'var(--color-text-primary)' }}>
                {m.content}
              </p>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={handleSend}
        className="flex items-center gap-2 px-4 py-3 border-t"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <input
          type="text"
          value={sendText}
          onChange={(e) => setSendText(e.target.value)}
          placeholder="Send a message..."
          disabled={sending}
          className="flex-1 text-xs px-3 py-1.5 rounded border bg-transparent outline-none"
          style={{
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-primary)',
          }}
        />
        <button
          type="submit"
          disabled={!sendText.trim() || sending}
          className="text-xs px-3 py-1.5 rounded font-medium"
          style={{
            background: sendText.trim() ? 'var(--color-accent)' : 'var(--color-surface-raised)',
            color: sendText.trim() ? '#fff' : 'var(--color-text-tertiary)',
            cursor: sendText.trim() ? 'pointer' : 'default',
          }}
        >
          Send
        </button>
      </form>
    </div>
  )
}
