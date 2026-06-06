import { useState, useEffect, useMemo, useCallback, type FormEvent } from 'react'
import { fetchApi } from '../api/client'
import { ChannelList, type Channel } from '../components/ChannelList'
import { ChannelView } from '../components/ChannelView'

interface CommsMessage {
  id: string
  channel: string
  from_agent: string
  content: string
  timestamp: string
  direction: 'inbound' | 'outbound' | 'internal'
}

export function CommsPanel() {
  const [messages, setMessages] = useState<CommsMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null)
  const [sendText, setSendText] = useState('')
  const [sending, setSending] = useState(false)

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

  const channelMap = useMemo(() => {
    const map = new Map<string, CommsMessage[]>()
    messages.forEach((m) => {
      const ch = m.channel || 'general'
      if (!map.has(ch)) map.set(ch, [])
      map.get(ch)!.push(m)
    })
    return map
  }, [messages])

  const channels: Channel[] = useMemo(() => {
    return Array.from(channelMap.entries())
      .map(([name, msgs]) => {
        const last = msgs[msgs.length - 1]
        return {
          name,
          lastMessage: last?.content?.slice(0, 60) || '',
          lastFrom: last?.from_agent || 'system',
          lastTime: last?.timestamp || '',
          count: msgs.length,
        }
      })
      .sort((a, b) => {
        if (!a.lastTime || !b.lastTime) return 0
        return new Date(b.lastTime).getTime() - new Date(a.lastTime).getTime()
      })
  }, [channelMap])

  const channelMessages = useMemo(() => {
    if (!selectedChannel) return []
    return channelMap.get(selectedChannel) || []
  }, [selectedChannel, channelMap])

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
          Comms
        </h2>
        <span className="ml-2 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
          Internal agent &amp; team communication
        </span>
        <span className="ml-auto text-xs tabular-nums" style={{ color: 'var(--color-text-tertiary)' }}>
          {messages.length}
        </span>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Channel sidebar */}
        <div className="w-60 shrink-0 border-r overflow-y-auto" style={{ borderColor: 'var(--color-border)' }}>
          {loading ? (
            <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--color-text-tertiary)' }}>
              Loading...
            </div>
          ) : (
            <ChannelList
              channels={channels}
              selected={selectedChannel}
              onSelect={setSelectedChannel}
            />
          )}
        </div>

        {/* Message view */}
        <div className="flex-1 flex flex-col min-w-0">
          {selectedChannel ? (
            <>
              <div className="flex-1 min-h-0">
                <ChannelView channel={selectedChannel} messages={channelMessages} />
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
                    background: sendText.trim() ? 'var(--color-cyan)' : 'var(--color-surface-raised)',
                    color: sendText.trim() ? 'var(--color-canvas)' : 'var(--color-text-tertiary)',
                    cursor: sendText.trim() ? 'pointer' : 'default',
                  }}
                >
                  Send
                </button>
              </form>
            </>
          ) : (
            <div className="flex items-center justify-center h-full">
              <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                Select a channel
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
