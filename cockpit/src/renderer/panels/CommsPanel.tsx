import { useState, useEffect, useMemo, useCallback, type FormEvent } from 'react'
import { fetchApi } from '../api/client'
import { ConversationList, type Conversation } from '../components/ChannelList'
import { ConversationView, type A2AMessage } from '../components/ChannelView'

export function CommsPanel() {
  const [messages, setMessages] = useState<A2AMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null)
  const [sendText, setSendText] = useState('')
  const [sendRecipient, setSendRecipient] = useState('dex')
  const [sending, setSending] = useState(false)

  const fetchMessages = useCallback(async () => {
    try {
      const data = await fetchApi<A2AMessage[]>('/comms?limit=200')
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

  const conversationMap = useMemo(() => {
    const map = new Map<string, A2AMessage[]>()
    messages.forEach((m) => {
      const convId = m.conversation_id || m.id
      if (!map.has(convId)) map.set(convId, [])
      map.get(convId)!.push(m)
    })
    return map
  }, [messages])

  const knownAgents = useMemo(() => {
    const agents = new Set<string>()
    messages.forEach((m) => {
      if (m.sender && m.sender !== 'operator') agents.add(m.sender)
      if (m.recipient && m.recipient !== 'operator') agents.add(m.recipient)
    })
    return Array.from(agents).sort()
  }, [messages])

  const conversations: Conversation[] = useMemo(() => {
    return Array.from(conversationMap.entries())
      .map(([convId, msgs]) => {
        const sorted = [...msgs].sort((a, b) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        )
        const last = sorted[sorted.length - 1]
        const participants = new Set<string>()
        msgs.forEach((m) => {
          if (m.sender) participants.add(m.sender)
          if (m.recipient) participants.add(m.recipient)
        })
        return {
          id: convId,
          label: Array.from(participants).join(' ↔ '),
          participants: Array.from(participants),
          lastMessage: last?.content?.slice(0, 80) || '',
          lastSender: last?.sender || 'system',
          lastTime: last?.timestamp || '',
          count: msgs.length,
          intent: last?.intent,
        }
      })
      .sort((a, b) => {
        if (!a.lastTime || !b.lastTime) return 0
        return new Date(b.lastTime).getTime() - new Date(a.lastTime).getTime()
      })
  }, [conversationMap])

  const conversationMessages = useMemo(() => {
    if (!selectedConversation) return []
    const msgs = conversationMap.get(selectedConversation) || []
    return [...msgs].sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )
  }, [selectedConversation, conversationMap])

  const selectedParticipants = useMemo(() => {
    if (!selectedConversation) return []
    const conv = conversations.find(c => c.id === selectedConversation)
    return conv?.participants || []
  }, [selectedConversation, conversations])

  const handleSend = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    const text = sendText.trim()
    if (!text || sending) return
    setSending(true)
    try {
      await fetchApi('/comms/send', {
        method: 'POST',
        body: JSON.stringify({ recipient: sendRecipient, content: text }),
      })
      setSendText('')
      await fetchMessages()
    } catch (err) {
      console.error('comms send failed:', err)
    } finally {
      setSending(false)
    }
  }, [sendText, sendRecipient, sending, fetchMessages])

  const intentCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    messages.forEach((m) => {
      const intent = m.intent || 'unknown'
      counts[intent] = (counts[intent] || 0) + 1
    })
    return counts
  }, [messages])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
          A2A Comms
        </h2>
        <div className="flex items-center gap-3 ml-3">
          {Object.entries(intentCounts).map(([intent, count]) => (
            <span key={intent} className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              {intent}: {count}
            </span>
          ))}
        </div>
        <span className="ml-auto text-xs tabular-nums" style={{ color: 'var(--color-text-tertiary)' }}>
          {conversations.length} threads / {messages.length} msgs
        </span>
      </div>

      <div className="flex flex-1 min-h-0">
        <div className="w-60 shrink-0 border-r overflow-y-auto" style={{ borderColor: 'var(--color-border)' }}>
          {loading ? (
            <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--color-text-tertiary)' }}>
              —
            </div>
          ) : (
            <ConversationList
              conversations={conversations}
              selected={selectedConversation}
              onSelect={setSelectedConversation}
            />
          )}
        </div>

        <div className="flex-1 flex flex-col min-w-0">
          {selectedConversation ? (
            <>
              <div className="flex-1 min-h-0">
                <ConversationView
                  conversationId={selectedConversation}
                  messages={conversationMessages}
                  participants={selectedParticipants}
                />
              </div>
              <form
                onSubmit={handleSend}
                className="flex items-center gap-2 px-4 py-3 border-t"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <select
                  value={sendRecipient}
                  onChange={(e) => setSendRecipient(e.target.value)}
                  className="text-[10px] px-2 py-2 rounded border bg-transparent font-mono"
                  style={{
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text-secondary)',
                    background: 'var(--color-surface)',
                  }}
                >
                  {knownAgents.length > 0 ? (
                    knownAgents.map((agent) => (
                      <option key={agent} value={agent}>{agent}</option>
                    ))
                  ) : (
                    <>
                      <option value="dex">dex</option>
                      <option value="advisor">advisor</option>
                      <option value="researcher">researcher</option>
                      <option value="builder">builder</option>
                    </>
                  )}
                </select>
                <input
                  type="text"
                  value={sendText}
                  onChange={(e) => setSendText(e.target.value)}
                  placeholder="Send a message..."
                  disabled={sending}
                  className="flex-1 text-xs px-3 py-2 rounded border bg-transparent outline-none"
                  style={{
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text-primary)',
                  }}
                />
                <button
                  type="submit"
                  disabled={!sendText.trim() || sending}
                  className="text-xs px-3 py-2 rounded font-medium"
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
              <div className="text-center">
                <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                  Select a conversation thread
                </p>
                <p className="text-[10px] mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
                  {conversations.length} active A2A threads
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
