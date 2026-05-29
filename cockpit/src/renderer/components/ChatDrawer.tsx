import React, { useRef, useEffect, type FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChatStore, type ChatMessage, type Provenance, type Attachment } from '../stores/chatStore'

function safeUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : ''
}

const markdownComponents = {
  a: ({ href, children, ...rest }: React.ComponentPropsWithoutRef<'a'>) => (
    <a href={href ?? ''} target="_blank" rel="noopener noreferrer nofollow" {...rest}>{children}</a>
  ),
  img: () => null,
}
import { useCockpitStore } from '../stores/cockpitStore'
import { useConfigStore } from '../stores/configStore'

const CHANNELS = [
  { id: 'cockpit', label: 'Cockpit', enabled: true },
  { id: 'discord', label: 'Discord', enabled: true },
  { id: 'telegram', label: 'Telegram', enabled: false },
  { id: 'whatsapp', label: 'WhatsApp', enabled: false },
  { id: 'slack', label: 'Slack', enabled: false },
] as const

const API_URL = import.meta.env.VITE_API_URL || '/api/umh'

function OriginBadge({ channel }: { channel?: string }) {
  if (!channel || channel === 'cockpit') {
    return (
      <span
        className="text-[9px] font-mono px-1 rounded"
        style={{ color: 'var(--color-text-tertiary)', background: 'var(--color-surface-raised)' }}
      >
        CMD
      </span>
    )
  }
  if (channel === 'discord') {
    return (
      <span
        className="text-[9px] font-mono px-1 rounded"
        style={{ color: '#7289da', background: 'rgba(114,137,218,0.12)' }}
      >
        DC
      </span>
    )
  }
  return (
    <span
      className="text-[9px] font-mono px-1 rounded"
      style={{ color: 'var(--color-text-tertiary)', background: 'var(--color-surface-raised)' }}
    >
      {channel.slice(0, 3).toUpperCase()}
    </span>
  )
}

function ProvenanceBlock({ provenance }: { provenance: Provenance }) {
  const entries: string[] = []
  if (provenance.node) entries.push(provenance.node)
  if (provenance.harness) entries.push(provenance.harness)
  if (provenance.session) entries.push(`session ${provenance.session}`)
  if (provenance.phase) entries.push(`Phase ${provenance.phase}`)
  if (provenance.pr) entries.push(`PR #${provenance.pr}`)
  if (provenance.task) entries.push(provenance.task)

  if (entries.length === 0) return null

  return (
    <div
      className="flex flex-wrap gap-x-1.5 gap-y-0.5 mt-1 mb-2 py-1 px-2 rounded text-[10px] font-mono"
      style={{
        background: 'var(--color-surface-raised)',
        borderLeft: '2px solid var(--color-cyan)',
        color: 'var(--color-text-tertiary)',
      }}
    >
      {entries.map((entry, i) => (
        <span key={i}>
          {i > 0 && <span style={{ opacity: 0.4 }}> · </span>}
          {entry}
        </span>
      ))}
    </div>
  )
}

function AttachmentBlock({ attachment }: { attachment: Attachment }) {
  const downloadUrl = `${API_URL}/chat/attachment?path=${encodeURIComponent(attachment.path)}`

  return (
    <a
      href={downloadUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2 mt-2 py-1.5 px-2 rounded text-xs font-mono no-underline transition-colors"
      style={{
        background: 'var(--color-surface-raised)',
        border: '1px solid var(--color-border)',
        color: 'var(--color-cyan)',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-cyan)' }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
    >
      <span style={{ fontSize: '14px' }}>&#x1F4CE;</span>
      <span className="truncate">{attachment.filename}</span>
      <span style={{ color: 'var(--color-text-tertiary)', marginLeft: 'auto', flexShrink: 0 }}>DOWNLOAD</span>
    </a>
  )
}

function MessageContent({ msg }: { msg: ChatMessage }) {
  const isReport = msg.intent === 'report'
  const isAssistant = msg.sender === 'assistant'

  const contentColor = isAssistant
    ? 'var(--color-violet)'
    : msg.sender === 'system'
      ? 'var(--color-cyan)'
      : 'var(--color-text-primary)'

  if (isReport) {
    return (
      <div>
        {msg.title && (
          <div
            className="font-mono text-xs tracking-wide uppercase mb-1 pb-1"
            style={{ color: 'var(--color-cyan)', borderBottom: '1px solid var(--color-border)' }}
          >
            {msg.title}
          </div>
        )}
        {msg.provenance && <ProvenanceBlock provenance={msg.provenance} />}
        <div className="chat-markdown leading-relaxed" style={{ color: contentColor }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} urlTransform={safeUrl} components={markdownComponents}>{msg.content}</ReactMarkdown>
        </div>
        {msg.attachment && <AttachmentBlock attachment={msg.attachment} />}
      </div>
    )
  }

  if (isAssistant || msg.sender === 'system') {
    return (
      <div className="chat-markdown leading-relaxed" style={{ color: contentColor }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} urlTransform={safeUrl} components={markdownComponents}>{msg.content}</ReactMarkdown>
      </div>
    )
  }

  return (
    <p className="leading-relaxed whitespace-pre-wrap" style={{ color: contentColor }}>
      {msg.content}
    </p>
  )
}

export function ChatDrawer() {
  const aiName = useConfigStore((s) => s.aiName)
  const chatOpen = useCockpitStore((s) => s.chatOpen)
  const messages = useChatStore((s) => s.messages)
  const input = useChatStore((s) => s.input)
  const sending = useChatStore((s) => s.sending)
  const error = useChatStore((s) => s.error)
  const targetChannel = useChatStore((s) => s.targetChannel)
  const setInput = useChatStore((s) => s.setInput)
  const setTargetChannel = useChatStore((s) => s.setTargetChannel)
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
              {aiName}
            </span>
            <span className="ml-2 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
              unified channel
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
            {messages.length === 0 && (
              <p className="text-center text-xs mt-8" style={{ color: 'var(--color-text-tertiary)' }}>
                Start a conversation with {aiName}
              </p>
            )}
            {messages.map((msg) => (
              <div key={msg.id} className="text-sm">
                <div className="flex items-center gap-2 mb-0.5">
                  <span
                    className="font-mono text-xs uppercase"
                    style={{
                      color: msg.sender === 'assistant'
                        ? 'var(--color-violet)'
                        : msg.sender === 'system'
                          ? 'var(--color-cyan)'
                          : 'var(--color-text-secondary)',
                    }}
                  >
                    {msg.sender === 'assistant' ? aiName : msg.sender === 'system' ? 'UMH' : 'YOU'}
                  </span>
                  {msg.intent === 'report' && (
                    <span
                      className="text-[9px] font-mono px-1 rounded uppercase"
                      style={{ color: 'var(--color-success)', background: 'rgba(0,255,136,0.08)' }}
                    >
                      report
                    </span>
                  )}
                  <OriginBadge channel={msg.origin_channel} />
                  {msg.source === 'voice' && (
                    <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>mic</span>
                  )}
                  <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <MessageContent msg={msg} />
              </div>
            ))}
            {sending && (
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs uppercase" style={{ color: 'var(--color-violet)' }}>{aiName}</span>
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
            className="flex items-center px-3 py-2 shrink-0 gap-2"
            style={{ borderTop: '1px solid var(--color-border)' }}
          >
            <select
              value={targetChannel}
              onChange={(e) => setTargetChannel(e.target.value)}
              className="bg-transparent text-xs font-mono outline-none cursor-pointer shrink-0"
              style={{ color: 'var(--color-text-tertiary)', maxWidth: '72px' }}
            >
              {CHANNELS.map((ch) => (
                <option key={ch.id} value={ch.id} disabled={!ch.enabled}>
                  {ch.label}{!ch.enabled ? ' ...' : ''}
                </option>
              ))}
            </select>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Message ${aiName}...`}
              disabled={sending}
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--color-text-tertiary)]"
              style={{ color: 'var(--color-text-primary)' }}
            />
            <button
              type="submit"
              disabled={!input.trim() || sending}
              className="px-2 py-1 rounded text-xs font-mono uppercase tracking-wider transition-colors shrink-0"
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
