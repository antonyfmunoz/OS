import { useRef, useEffect, type FormEvent } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useCockpitStore } from '../stores/cockpitStore'

export function ChatDrawer() {
  const chatOpen = useCockpitStore((s) => s.chatOpen)
  const messages = useChatStore((s) => s.messages)
  const input = useChatStore((s) => s.input)
  const sending = useChatStore((s) => s.sending)
  const error = useChatStore((s) => s.error)
  const setInput = useChatStore((s) => s.setInput)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (chatOpen) inputRef.current?.focus()
  }, [chatOpen])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (input.trim() && !sending) {
      sendMessage(input)
    }
  }

  return (
    <aside
      className="flex flex-col overflow-hidden transition-all"
      style={{
        width: chatOpen ? 'var(--spacing-chat-width)' : '0px',
        minWidth: chatOpen ? 'var(--spacing-chat-width)' : '0px',
        background: 'var(--color-surface)',
        borderLeft: chatOpen ? '1px solid var(--color-border)' : 'none',
        transitionDuration: 'var(--transition-normal)',
      }}
    >
      {chatOpen && (
        <>
          {/* Header */}
          <div
            className="flex items-center px-3 h-10 shrink-0"
            style={{ borderBottom: '1px solid var(--color-border)' }}
          >
            <span className="font-mono text-xs tracking-wider uppercase" style={{ color: 'var(--color-violet)' }}>
              DEX
            </span>
            <span className="ml-2 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
              intelligence channel
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
            {messages.length === 0 && (
              <p className="text-center text-xs mt-8" style={{ color: 'var(--color-text-tertiary)' }}>
                Start a conversation with DEX
              </p>
            )}
            {messages.map((msg) => (
              <div key={msg.id} className="text-sm">
                <div className="flex items-center gap-2 mb-0.5">
                  <span
                    className="font-mono text-xs uppercase"
                    style={{
                      color: msg.sender === 'dex' ? 'var(--color-violet)' : 'var(--color-text-secondary)',
                    }}
                  >
                    {msg.sender === 'dex' ? 'DEX' : 'YOU'}
                  </span>
                  {msg.source === 'voice' && (
                    <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>🎤</span>
                  )}
                  <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <p
                  className="leading-relaxed whitespace-pre-wrap"
                  style={{
                    color: msg.sender === 'dex' ? 'var(--color-violet)' : 'var(--color-text-primary)',
                  }}
                >
                  {msg.content}
                </p>
              </div>
            ))}
            {sending && (
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs uppercase" style={{ color: 'var(--color-violet)' }}>DEX</span>
                <span className="text-xs animate-pulse" style={{ color: 'var(--color-text-tertiary)' }}>thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Error */}
          {error && (
            <div className="px-3 py-1.5 text-xs" style={{ color: 'var(--color-danger)', background: 'var(--color-surface-raised)' }}>
              {error}
            </div>
          )}

          {/* Input */}
          <form
            onSubmit={handleSubmit}
            className="flex items-center px-3 py-2 shrink-0"
            style={{ borderTop: '1px solid var(--color-border)' }}
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message DEX..."
              disabled={sending}
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--color-text-tertiary)]"
              style={{ color: 'var(--color-text-primary)' }}
            />
            <button
              type="submit"
              disabled={!input.trim() || sending}
              className="ml-2 px-2 py-1 rounded text-xs font-mono uppercase tracking-wider transition-colors"
              style={{
                color: input.trim() ? 'var(--color-cyan)' : 'var(--color-text-tertiary)',
                background: input.trim() ? 'var(--color-cyan-glow)' : 'transparent',
              }}
            >
              send
            </button>
          </form>
        </>
      )}
    </aside>
  )
}
