import { clsx } from 'clsx'
import React, { useState, useRef, useEffect } from 'react'
import { ChevronLeft, ChevronRight, MessageSquare, Activity, Terminal, Send, Pencil, Check, Download } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useSystemStore } from '../stores/systemStore'
import { useChatStore, type ChatMessage, type Provenance, type Attachment } from '../stores/chatStore'
import { usePolling } from '../hooks/usePolling'
import { relativeTime } from '../lib/time'
import { useConfigStore } from '../stores/configStore'

const API_URL = import.meta.env.VITE_API_URL || '/api/umh'

function safeUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : ''
}

const markdownComponents = {
  a: ({ href, children, ...rest }: React.ComponentPropsWithoutRef<'a'>) => (
    <a href={href ?? ''} target="_blank" rel="noopener noreferrer nofollow" {...rest}>{children}</a>
  ),
  img: () => null,
}

type RightTab = 'chat' | 'activity' | 'logs'

export function RightRail() {
  const [collapsed, setCollapsed] = useState(false)
  const [activeTab, setActiveTab] = useState<RightTab>('chat')
  const traces = useSystemStore((s) => s.traces)
  const fetchTraces = useSystemStore((s) => s.fetchTraces)

  usePolling(fetchTraces, 5000)

  const tabs: Array<{ id: RightTab; icon: typeof MessageSquare; label: string }> = [
    { id: 'chat', icon: MessageSquare, label: 'Chat' },
    { id: 'activity', icon: Activity, label: 'Activity' },
    { id: 'logs', icon: Terminal, label: 'Logs' },
  ]

  if (collapsed) {
    return (
      <div className="flex flex-col items-center py-2 w-10 bg-surface border-l border-border">
        <button onClick={() => setCollapsed(false)} className="p-1 text-text-tertiary hover:text-cyan">
          <ChevronLeft size={14} />
        </button>
        {tabs.map((t) => {
          const Icon = t.icon
          return (
            <button
              key={t.id}
              onClick={() => { setCollapsed(false); setActiveTab(t.id) }}
              className={clsx('p-2 mt-1', activeTab === t.id ? 'text-cyan' : 'text-text-tertiary')}
              title={t.label}
            >
              <Icon size={14} />
            </button>
          )
        })}
      </div>
    )
  }

  return (
    <div className="flex flex-col w-[320px] bg-surface border-l border-border">
      {/* Tab bar */}
      <div className="flex items-center border-b border-border px-2 h-9 shrink-0">
        {tabs.map((t) => {
          const Icon = t.icon
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={clsx(
                'flex items-center gap-1.5 px-2 py-1 text-[10px] font-mono uppercase tracking-wider transition-colors',
                activeTab === t.id ? 'text-cyan' : 'text-text-tertiary hover:text-text-secondary',
              )}
            >
              <Icon size={12} />
              {t.label}
            </button>
          )
        })}
        <div className="flex-1" />
        <button onClick={() => setCollapsed(true)} className="p-1 text-text-tertiary hover:text-cyan">
          <ChevronRight size={14} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {activeTab === 'chat' && <ChatSection />}
        {activeTab === 'activity' && <ActivitySection traces={traces} />}
        {activeTab === 'logs' && <LogsSection traces={traces} />}
      </div>
    </div>
  )
}

function ProvenanceLine({ provenance }: { provenance: Provenance }) {
  const parts: string[] = []
  if (provenance.node) parts.push(provenance.node)
  if (provenance.harness) parts.push(provenance.harness)
  if (provenance.session) parts.push(`session ${provenance.session}`)
  if (provenance.phase) parts.push(`Phase ${provenance.phase}`)
  if (provenance.pr) parts.push(`PR #${provenance.pr}`)
  if (provenance.task) parts.push(provenance.task)
  if (parts.length === 0) return null

  return (
    <div
      className="flex flex-wrap gap-x-1 gap-y-0.5 mt-1 mb-1.5 py-0.5 px-1.5 rounded text-[9px] font-mono"
      style={{
        background: 'var(--color-surface)',
        borderLeft: '2px solid var(--color-cyan)',
        color: 'var(--color-text-tertiary)',
      }}
    >
      {parts.map((p, i) => (
        <span key={i}>
          {i > 0 && <span style={{ opacity: 0.4 }}> · </span>}
          {p}
        </span>
      ))}
    </div>
  )
}

function AttachmentLink({ attachment }: { attachment: Attachment }) {
  const href = `${API_URL}/chat/attachment?path=${encodeURIComponent(attachment.path)}`
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-1.5 mt-1.5 py-1 px-1.5 rounded text-[10px] font-mono no-underline transition-colors"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        color: 'var(--color-cyan)',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-cyan)' }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
    >
      <Download size={10} />
      <span className="truncate flex-1">{attachment.filename}</span>
      <span style={{ color: 'var(--color-text-tertiary)' }}>DOWNLOAD</span>
    </a>
  )
}

function MessageBubble({ msg, aiName }: { msg: ChatMessage; aiName: string }) {
  if (msg.sender === 'operator') {
    return (
      <div className="px-2 py-1.5 rounded text-[11px] bg-cyan-glow text-text-primary ml-4">
        <div className="font-mono text-[9px] text-text-tertiary mb-0.5">YOU</div>
        <p className="whitespace-pre-wrap">{msg.content}</p>
      </div>
    )
  }

  const isReport = msg.intent === 'report'

  return (
    <div className="px-2 py-1.5 rounded text-[11px] bg-surface-raised text-text-secondary mr-4">
      <div className="flex items-center gap-1.5 mb-0.5">
        <span className="font-mono text-[9px] text-text-tertiary">{aiName}</span>
        {isReport && (
          <span
            className="text-[8px] font-mono px-1 rounded uppercase"
            style={{ color: 'var(--color-ok)', background: 'rgba(0,255,136,0.08)' }}
          >
            report
          </span>
        )}
        <span className="text-[9px] text-text-tertiary ml-auto">
          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      {isReport && msg.title && (
        <div
          className="font-mono text-[10px] tracking-wide uppercase mb-1 pb-0.5"
          style={{ color: 'var(--color-cyan)', borderBottom: '1px solid var(--color-border)' }}
        >
          {msg.title}
        </div>
      )}
      {msg.provenance && <ProvenanceLine provenance={msg.provenance} />}
      <div className="chat-markdown leading-relaxed" style={{ color: 'var(--color-violet)' }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} urlTransform={safeUrl} components={markdownComponents}>{msg.content}</ReactMarkdown>
      </div>
      {msg.attachment && <AttachmentLink attachment={msg.attachment} />}
    </div>
  )
}

function ChatSection() {
  const aiName = useConfigStore((s) => s.aiName)
  const messages = useChatStore((s) => s.messages)
  const input = useChatStore((s) => s.input)
  const sending = useChatStore((s) => s.sending)
  const setInput = useChatStore((s) => s.setInput)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const loadHistory = useChatStore((s) => s.loadHistory)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [assistantName, setAssistantName] = useState(`${aiName} ASSISTANT`)
  const [editingName, setEditingName] = useState(false)
  const [nameInput, setNameInput] = useState(assistantName)
  const nameRef = useRef<HTMLInputElement>(null)

  useEffect(() => { loadHistory() }, [loadHistory])
  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight) }, [messages])
  useEffect(() => { if (editingName) nameRef.current?.focus() }, [editingName])

  const handleSend = () => { if (input.trim()) sendMessage(input) }

  const commitName = () => {
    const trimmed = nameInput.trim()
    if (trimmed) setAssistantName(trimmed)
    else setNameInput(assistantName)
    setEditingName(false)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-1.5 mb-2">
        {editingName ? (
          <>
            <input
              ref={nameRef}
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') commitName(); if (e.key === 'Escape') { setNameInput(assistantName); setEditingName(false) } }}
              onBlur={commitName}
              className="wv-label bg-transparent border-b border-cyan outline-none flex-1 uppercase"
              style={{ fontSize: 'inherit', lineHeight: 'inherit' }}
            />
            <button onClick={commitName} className="p-0.5 text-cyan hover:text-text-primary transition-colors">
              <Check size={10} />
            </button>
          </>
        ) : (
          <>
            <span className="wv-label">{assistantName}</span>
            <button onClick={() => { setNameInput(assistantName); setEditingName(true) }} className="p-0.5 text-text-tertiary hover:text-cyan transition-colors">
              <Pencil size={10} />
            </button>
          </>
        )}
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 mb-2">
        {messages.map((m) => (
          <MessageBubble key={m.id} msg={m} aiName={aiName} />
        ))}
        {messages.length === 0 && (
          <p className="text-[11px] text-text-tertiary text-center py-4">Ask {aiName} anything</p>
        )}
      </div>
      <div className="flex items-center gap-1 border-t border-border pt-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
          placeholder={`Message ${aiName}...`}
          className="flex-1 text-[11px] px-2 py-1.5 rounded bg-surface-raised text-text-primary border border-border outline-none placeholder:text-text-tertiary"
          disabled={sending}
        />
        <button onClick={handleSend} disabled={sending || !input.trim()} className="p-1.5 rounded text-cyan hover:bg-cyan-glow transition-colors disabled:opacity-30">
          <Send size={12} />
        </button>
      </div>
    </div>
  )
}

function ActivitySection({ traces }: { traces: Array<{ id: string; timestamp: string; agent: string; action: string; status: string }> }) {
  const statusIcon: Record<string, string> = { running: '◉', completed: '✓', failed: '✗', pending: '○' }
  const statusColor: Record<string, string> = { running: 'text-cyan', completed: 'text-ok', failed: 'text-danger', pending: 'text-text-tertiary' }

  return (
    <div>
      <div className="wv-label mb-2">AGENT ACTIVITY</div>
      <div className="space-y-1">
        {traces.slice(0, 30).map((t) => (
          <div key={t.id} className="flex items-start gap-2 py-1 border-b border-border/50">
            <span className={clsx('w-3 text-center text-[11px]', statusColor[t.status])}>
              {statusIcon[t.status] || '○'}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-[11px] text-text-primary truncate">{t.action}</p>
              <p className="text-[10px] text-text-tertiary">{t.agent} · {relativeTime(t.timestamp)}</p>
            </div>
          </div>
        ))}
        {traces.length === 0 && (
          <p className="text-[11px] text-text-tertiary text-center py-4">No recent activity</p>
        )}
      </div>
    </div>
  )
}

function LogsSection({ traces }: { traces: Array<{ id: string; timestamp: string; agent: string; action: string; status: string }> }) {
  const completed = traces.filter((t) => t.status === 'completed' || t.status === 'failed')
  return (
    <div>
      <div className="wv-label mb-2">EXECUTION LOGS</div>
      <div className="space-y-1 font-mono text-[10px]">
        {completed.slice(0, 50).map((t) => (
          <div key={t.id} className={clsx('py-0.5', t.status === 'failed' ? 'text-danger' : 'text-text-secondary')}>
            [{t.status === 'completed' ? 'OK' : 'FAIL'}] {t.agent}: {t.action.slice(0, 60)}
          </div>
        ))}
        {completed.length === 0 && (
          <p className="text-text-tertiary text-center py-4">No execution logs</p>
        )}
      </div>
    </div>
  )
}
