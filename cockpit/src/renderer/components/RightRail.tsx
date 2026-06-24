import { clsx } from 'clsx'
import React, { useState, useRef, useEffect, useCallback } from 'react'
import { ChevronLeft, ChevronRight, MessageSquare, FolderOpen, Play, Send, Pencil, Check, Download, Mic, MicOff } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChatStore, type ChatMessage, type Provenance, type Attachment } from '../stores/chatStore'
import { usePolling } from '../hooks/usePolling'
import { useConfigStore } from '../stores/configStore'
import { useCollapseStore } from '../stores/collapseStore'
import { useViewContextStore } from '../stores/viewContextStore'
import { useVoiceStore } from '../stores/voiceStore'
import { startVoice, stopVoice } from '../api/voice-controller'
import { getApiKey } from '../api/client'
import { fetchApi } from '../api/client'
import type { SuggestedAction } from '../stores/chatStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { useExecutionSummaryStore } from '../stores/executionSummaryStore'
import { VoiceRouteHud } from './VoiceRouteHud'

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

type RightTab = 'conversation' | 'context' | 'execution'

export function RightRail() {
  const collapsed = useCollapseStore((s) => !s.isOpen('right-rail'))
  const toggleCollapsed = useCallback(() => useCollapseStore.getState().toggle('right-rail'), [])
  const [activeTab, setActiveTab] = useState<RightTab>('conversation')

  const tabs: Array<{ id: RightTab; icon: typeof MessageSquare; label: string }> = [
    { id: 'conversation', icon: MessageSquare, label: 'Chat' },
    { id: 'context', icon: FolderOpen, label: 'Context' },
    { id: 'execution', icon: Play, label: 'Execution' },
  ]

  if (collapsed) {
    return (
      <div className="flex flex-col items-center py-2 w-10 bg-surface border-l border-border">
        <button onClick={toggleCollapsed} className="p-1 text-text-tertiary hover:text-cyan">
          <ChevronLeft size={14} />
        </button>
        {tabs.map((t) => {
          const Icon = t.icon
          return (
            <button
              key={t.id}
              onClick={() => { toggleCollapsed(); setActiveTab(t.id) }}
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
    <div className="flex flex-col w-[240px] bg-surface border-l border-border">
      {/* Tab bar — mirrored from LeftRail: collapse on inner edge, tabs on outer (right) edge */}
      <div className="flex items-center border-b border-border px-2 h-9 shrink-0">
        <button onClick={toggleCollapsed} className="p-1 text-text-tertiary hover:text-cyan transition-colors shrink-0">
          <ChevronRight size={14} />
        </button>
        <div className="flex items-center justify-end flex-1 min-w-0">
          {tabs.map((t) => {
            const Icon = t.icon
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={clsx(
                  'flex items-center gap-1 px-1.5 py-1 text-[10px] font-mono uppercase tracking-wider leading-none transition-colors',
                  activeTab === t.id ? 'text-cyan' : 'text-text-tertiary hover:text-text-secondary',
                )}
              >
                <Icon size={12} />
                {t.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {activeTab === 'conversation' && <ChatSection />}
        {activeTab === 'context' && <ContextSection />}
        {activeTab === 'execution' && <ExecutionSection />}
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
      className="flex flex-wrap gap-x-1 gap-y-1 mt-1 mb-2 py-1 px-2 rounded text-[9px] font-mono"
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
  const handleDownload = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault()
    const url = `${API_URL}/chat/attachment?path=${encodeURIComponent(attachment.path)}`
    const headers: Record<string, string> = {}
    const key = getApiKey()
    if (key) headers['X-API-Key'] = key
    const res = await fetch(url, { headers })
    if (!res.ok) return
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = attachment.filename
    a.click()
    URL.revokeObjectURL(a.href)
  }, [attachment])

  return (
    <button
      type="button"
      onClick={handleDownload}
      className="flex items-center gap-2 mt-2 py-1 px-2 rounded text-[10px] font-mono transition-colors cursor-pointer w-full text-left"
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
    </button>
  )
}

function MessageBubble({ msg, aiName, onAction }: { msg: ChatMessage; aiName: string; onAction?: (a: SuggestedAction) => void }) {
  if (msg.sender === 'operator') {
    return (
      <div className="px-2 py-2 rounded text-[11px] bg-cyan-glow text-text-primary ml-4">
        <div className="flex items-center gap-1 font-mono text-[9px] text-text-tertiary mb-1">
          <span>YOU</span>
          {msg.source === 'voice' && (
            <span className="text-[8px] px-1 rounded bg-violet/10 text-violet/70">
              <Mic size={8} className="inline" /> voice
            </span>
          )}
        </div>
        <p className="whitespace-pre-wrap">{msg.content}</p>
      </div>
    )
  }

  const isReport = msg.intent === 'report'

  return (
    <div className="px-2 py-2 rounded text-[11px] bg-surface-raised text-text-secondary mr-4">
      <div className="flex items-center gap-2 mb-1">
        <span className="font-mono text-[9px] text-text-tertiary">{aiName}</span>
        {isReport && (
          <span
            className="text-[8px] font-mono px-1 rounded uppercase"
            style={{ color: 'var(--color-ok)', background: 'rgba(0,255,136,0.08)' }}
          >
            report
          </span>
        )}
        {msg.intent && msg.intent !== 'report' && msg.intent !== 'dex_response' && (
          <span className="text-[8px] font-mono px-1 rounded uppercase text-text-tertiary bg-surface">
            {msg.intent}
          </span>
        )}
        {msg.metadata?.target_node && (
          <span
            className="text-[8px] font-mono px-1 rounded uppercase"
            style={{
              color: msg.metadata.target_node === 'vps' ? 'var(--color-warn)'
                : msg.metadata.target_node === 'beast_windows' ? 'var(--color-cyan)'
                : 'var(--color-ok)',
              background: msg.metadata.target_node === 'vps' ? 'rgba(255,204,0,0.08)'
                : msg.metadata.target_node === 'beast_windows' ? 'rgba(0,255,255,0.08)'
                : 'rgba(0,255,136,0.08)',
            }}
          >
            {msg.metadata.target_node === 'beast_windows' ? 'beast' : String(msg.metadata.target_node)}
          </span>
        )}
        <span className="text-[9px] text-text-tertiary ml-auto flex items-center gap-1">
          {msg.metadata?.model_tier && msg.metadata.model_tier !== 'deterministic' && (
            <span className="text-[8px] font-mono px-1 rounded bg-violet/10 text-violet/70">
              via {String(msg.metadata.model_tier)}
            </span>
          )}
          {msg.metadata?.model_tier === 'deterministic' && (
            <span className="text-[8px] font-mono px-1 rounded bg-warn/10 text-warn/70">
              offline
            </span>
          )}
          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      {isReport && msg.title && (
        <div
          className="font-mono text-[10px] tracking-wide uppercase mb-1 pb-1"
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
      {msg.suggested_actions && msg.suggested_actions.length > 0 && onAction && (() => {
        const filtered = msg.suggested_actions!.filter(
          (a) => a.action !== 'approve_engineering_plan' && a.action !== 'reject_engineering_plan'
        )
        return filtered.length > 0 ? (
          <div className="flex flex-wrap gap-1 mt-1.5 pt-1.5 border-t border-border/50">
            {filtered.map((action, i) => (
              <button
                key={i}
                onClick={() => onAction(action)}
                className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-cyan/30 text-cyan hover:bg-cyan-glow transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
        ) : null
      })()}
    </div>
  )
}

function ChatSection() {
  const aiName = useConfigStore((s) => s.aiName)
  const setConfigValue = useConfigStore((s) => s.setConfigValue)
  const messages = useChatStore((s) => s.messages)
  const input = useChatStore((s) => s.input)
  const sending = useChatStore((s) => s.sending)
  const error = useChatStore((s) => s.error)
  const setInput = useChatStore((s) => s.setInput)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const viewContext = useViewContextStore((s) => s.context)
  const setPanel = useCockpitStore((s) => s.setPanel)
  const micState = useVoiceStore((s) => s.micState)
  const ttsState = useVoiceStore((s) => s.ttsState)
  const voiceError = useVoiceStore((s) => s.error)
  const voicePresentationStatus = useVoiceStore((s) => s.voicePresentationStatus)
  const draftMessage = useChatStore((s) => s.draftMessage)
  const placeholderMessage = useChatStore((s) => s.placeholderMessage)
  const scrollRef = useRef<HTMLDivElement>(null)
  const displayName = aiName
  const [editingName, setEditingName] = useState(false)
  const [nameInput, setNameInput] = useState(aiName)
  const nameRef = useRef<HTMLInputElement>(null)
  const [voiceAvailable, setVoiceAvailable] = useState(true)

  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight) }, [messages])
  useEffect(() => { if (editingName) nameRef.current?.focus() }, [editingName])
  useEffect(() => { setNameInput(aiName) }, [aiName])

  useEffect(() => {
    if (typeof navigator.mediaDevices === 'undefined') {
      setVoiceAvailable(false)
    }
  }, [])

  const handleSend = () => {
    if (input.trim()) {
      const ctx: Record<string, unknown> = { ...viewContext }
      sendMessage(input, 'text', ctx)
    }
  }

  const handleMicToggle = useCallback(() => {
    if (micState === 'idle') {
      setVoiceAvailable(true)
      startVoice().catch(() => {
        setVoiceAvailable(false)
      })
    } else {
      stopVoice()
    }
  }, [micState])

  const handleSuggestedAction = useCallback((action: SuggestedAction) => {
    switch (action.action) {
      case 'query':
        sendMessage(action.payload.content as string, 'text', { ...viewContext })
        break
      case 'navigate':
        if (action.payload.panel) setPanel(action.payload.panel as string)
        break
      case 'cc_send':
        fetchApi('/claude-session/send', {
          method: 'POST',
          body: JSON.stringify(action.payload),
        }).then((res) => {
          const r = res as Record<string, unknown>
          const msg = r.ok ? 'Sent to Claude Code session.' : `Claude Code: ${r.error || 'unavailable'}`
          sendMessage(msg, 'text')
        }).catch(() => sendMessage('Claude Code bridge unavailable.', 'text'))
        break
      case 'council':
        fetchApi('/council/review', {
          method: 'POST',
          body: JSON.stringify(action.payload),
        }).then(() => sendMessage('Council review submitted.', 'text'))
          .catch(() => sendMessage('Council review failed.', 'text'))
        break
      case 'decompose':
        fetchApi('/command-center/work-packets/decompose', {
          method: 'POST',
          body: JSON.stringify(action.payload),
        }).then(() => sendMessage('Intent decomposed into work packets.', 'text'))
          .catch(() => sendMessage('Decomposition failed.', 'text'))
        break
      case 'engineering_plan':
        import('../stores/engineeringStore').then(({ useEngineeringStore }) => {
          useEngineeringStore.getState().createPlan(action.payload.intent as string)
          setPanel('engineering')
          sendMessage('Engineering plan created.', 'text')
        }).catch(() => sendMessage('Failed to create engineering plan.', 'text'))
        break
      case 'approve_engineering_plan':
        fetchApi(`/engineering/plans/${action.payload.plan_id}/approve`, {
          method: 'POST',
        }).then(() => {
          sendMessage(`Plan ${action.payload.plan_id} approved. Work packets generated.`, 'text')
          return fetchApi(`/engineering/plans/${action.payload.plan_id}/dispatch`, {
            method: 'POST',
            body: JSON.stringify({ node_id: 'windows-desktop' }),
          })
        }).then((res) => {
          const r = res as Record<string, unknown>
          sendMessage(`Dispatched to Beast: ${r.dispatched || 0} tasks sent.`, 'text')
        }).catch(() => sendMessage('Plan approval or dispatch failed.', 'text'))
        break
      case 'reject_engineering_plan':
        fetchApi(`/engineering/plans/${action.payload.plan_id}/reject`, {
          method: 'POST',
        }).then(() => sendMessage(`Plan ${action.payload.plan_id} rejected.`, 'text'))
          .catch(() => sendMessage('Plan rejection failed.', 'text'))
        break
      default:
        break
    }
  }, [sendMessage, viewContext, setPanel])

  const commitName = () => {
    const trimmed = nameInput.trim()
    if (trimmed && trimmed !== aiName) {
      setConfigValue('ai_name', trimmed)
    }
    if (!trimmed) setNameInput(aiName)
    setEditingName(false)
  }

  const voiceLabel = micState === 'requesting_permission' ? 'Requesting mic...'
    : micState === 'connecting_voice_ws' ? 'Connecting...'
    : micState === 'listening' ? 'Listening — tap to send'
    : micState === 'recording' ? 'Recording — tap to send'
    : micState === 'transcribing' ? 'Transcribing...'
    : micState === 'processing' ? 'Thinking...'
    : micState === 'interrupted' ? 'Listening — tap to send'
    : ttsState === 'generating_tts' ? 'Preparing voice...'
    : ttsState === 'speaking' ? 'Speaking...'
    : ttsState === 'tts_failed' ? 'Voice unavailable — showing text'
    : voiceError ? voiceError
    : null

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-2">
        {editingName ? (
          <>
            <input
              ref={nameRef}
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') commitName(); if (e.key === 'Escape') { setNameInput(aiName); setEditingName(false) } }}
              onBlur={commitName}
              className="wv-label bg-transparent border-b border-cyan outline-none flex-1 uppercase"
              style={{ fontSize: 'inherit', lineHeight: 'inherit' }}
            />
            <button onClick={commitName} className="p-1 text-cyan hover:text-text-primary transition-colors">
              <Check size={10} />
            </button>
          </>
        ) : (
          <>
            <span className="wv-label">{displayName}</span>
            <button onClick={() => { setNameInput(aiName); setEditingName(true) }} className="p-1 text-text-tertiary hover:text-cyan transition-colors">
              <Pencil size={10} />
            </button>
          </>
        )}
      </div>
      <VoiceRouteHud />
      {(viewContext.active_route || viewContext.selected_object_type) && (
        <div className="text-[9px] font-mono text-text-tertiary mb-1 px-1 py-0.5 bg-surface rounded border border-border truncate">
          Viewing: {viewContext.active_route}
          {viewContext.selected_object_type && ` > ${viewContext.selected_object_type}`}
          {viewContext.selected_object_summary && `: ${viewContext.selected_object_summary}`}
        </div>
      )}
      {error && (
        <div className="text-[9px] font-mono text-danger mb-1 px-1.5 py-1 bg-danger/10 rounded border border-danger/30">
          {error}
        </div>
      )}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 mb-2">
        {messages.map((m) => (
          <MessageBubble key={m.id} msg={m} aiName={aiName} onAction={handleSuggestedAction} />
        ))}
        {draftMessage && (
          <div className="px-2 py-2 rounded text-[11px] bg-cyan-glow text-text-primary ml-4 opacity-70">
            <div className="flex items-center gap-1 font-mono text-[9px] text-text-tertiary mb-1">
              <span>YOU</span>
              <span className="text-[8px] px-1 rounded bg-violet/10 text-violet/70">
                <Mic size={8} className="inline" /> speaking...
              </span>
            </div>
            <p className="whitespace-pre-wrap">{draftMessage.content || '...'}</p>
          </div>
        )}
        {(sending || voicePresentationStatus === 'thinking' || voicePresentationStatus === 'preparing_response') && (
          <div className="px-2 py-1.5 rounded text-[11px] bg-surface-raised text-text-tertiary mr-4 animate-pulse">
            {aiName} is thinking...
          </div>
        )}
        {(voicePresentationStatus === 'preparing_voice' || voicePresentationStatus === 'ready_to_commit') && (
          <div className="px-2 py-1.5 rounded text-[11px] bg-surface-raised text-text-tertiary mr-4 animate-pulse">
            {aiName} is preparing voice...
          </div>
        )}
        {placeholderMessage && voicePresentationStatus === 'idle' && (
          <div className="px-2 py-1.5 rounded text-[11px] bg-surface-raised text-text-tertiary mr-4 animate-pulse">
            {placeholderMessage.content}
          </div>
        )}
        {ttsState === 'tts_failed' && voiceError && voiceError.startsWith('Tap to play') && (
          <button
            onClick={() => {
              startVoice().catch(() => { /* ignore */ })
            }}
            className="px-2 py-1.5 rounded text-[10px] font-mono text-cyan border border-cyan/30 hover:bg-cyan-glow transition-colors cursor-pointer"
          >
            Tap to play audio
          </button>
        )}
        {messages.length === 0 && !sending && !draftMessage && (
          <p className="text-[11px] text-text-tertiary text-center py-4">Ask {aiName} anything</p>
        )}
      </div>
      <div className="flex flex-col gap-1 border-t border-border pt-2">
        {voiceLabel && (
          <div className={clsx(
            'text-[9px] font-mono px-1',
            voiceError ? 'text-danger' :
            (micState === 'recording') ? 'text-cyan font-bold' :
            'text-cyan animate-pulse',
          )}>{voiceLabel}</div>
        )}
        {voiceError && micState === 'idle' && (
          <button onClick={handleMicToggle} className="text-[9px] font-mono text-cyan/70 px-1 hover:text-cyan cursor-pointer">Try again</button>
        )}
        <div className="flex items-center gap-1">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
            placeholder={`Message ${aiName}...`}
            className="flex-1 text-[11px] px-2 py-1.5 rounded bg-surface-raised text-text-primary border border-border outline-none placeholder:text-text-tertiary"
            disabled={sending}
          />
          <button
            onClick={handleMicToggle}
            disabled={!voiceAvailable || micState === 'requesting_permission' || micState === 'connecting_voice_ws' || micState === 'transcribing' || micState === 'processing'}
            className={clsx(
              'p-1.5 rounded transition-colors',
              !voiceAvailable ? 'text-text-tertiary opacity-30 cursor-not-allowed' :
              (micState === 'listening' || micState === 'recording') ? 'text-danger bg-danger/10' :
              (micState === 'requesting_permission' || micState === 'connecting_voice_ws' || micState === 'transcribing') ? 'text-amber opacity-60' :
              'text-text-tertiary hover:text-cyan',
            )}
            title={!voiceAvailable ? (voiceError || 'Voice requires desktop app or HTTPS') : (micState === 'listening' || micState === 'recording') ? 'Tap to send' : 'Voice input'}
          >
            {(micState === 'listening' || micState === 'recording') ? <MicOff size={12} /> : <Mic size={12} />}
          </button>
          <button onClick={handleSend} disabled={sending || !input.trim()} className="p-1.5 rounded text-cyan hover:bg-cyan-glow transition-colors disabled:opacity-30">
            <Send size={12} />
          </button>
        </div>

      </div>
    </div>
  )
}

function ContextSection() {
  const [ctx, setCtx] = useState<Record<string, unknown> | null>(null)
  const [presence, setPresence] = useState<Record<string, unknown> | null>(null)

  usePolling(useCallback(() => {
    fetchApi('/meta-ide-context/context').then(setCtx).catch(() => {})
    fetchApi('/orchestrator-presence/snapshot').then(setPresence).catch(() => {})
  }, []), 5000, true, 750)

  const project = (presence?.active_project as string) || ''
  const repo = (presence?.active_repo as string) || ''
  const directory = (ctx?.active_directory as string) || ''
  const branch = (ctx?.active_branch as string) || ''
  const goals = (ctx?.related_goals as Array<Record<string, string>>) || []
  const decisions = (ctx?.related_decisions as Array<Record<string, string>>) || []
  const constraints = (ctx?.constraints as string[]) || []
  const activeFiles = (ctx?.active_files as string[]) || []

  return (
    <div className="space-y-3">
      <div className="wv-label mb-2">PROJECT CONTEXT</div>
      {project && <div className="text-[11px]"><span className="text-text-tertiary">Project</span> <span className="text-text-primary">{project}</span></div>}
      {repo && <div className="text-[11px]"><span className="text-text-tertiary">Repo</span> <span className="text-text-primary">{repo}</span></div>}
      {branch && <div className="text-[11px]"><span className="text-text-tertiary">Branch</span> <span className="text-cyan">{branch}</span></div>}
      {directory && <div className="text-[11px]"><span className="text-text-tertiary">Dir</span> <span className="text-text-secondary font-mono">{directory}</span></div>}

      {goals.length > 0 && (
        <div>
          <div className="wv-label mb-1">GOALS</div>
          {goals.slice(0, 5).map((g, i) => (
            <div key={i} className="text-[11px] text-text-secondary py-0.5">{g.title || g.description || JSON.stringify(g)}</div>
          ))}
        </div>
      )}

      {decisions.length > 0 && (
        <div>
          <div className="wv-label mb-1">DECISIONS</div>
          {decisions.slice(0, 5).map((d, i) => (
            <div key={i} className="text-[11px] text-text-secondary py-0.5">{d.title || d.description || JSON.stringify(d)}</div>
          ))}
        </div>
      )}

      {constraints.length > 0 && (
        <div>
          <div className="wv-label mb-1">CONSTRAINTS</div>
          {constraints.slice(0, 5).map((c, i) => (
            <div key={i} className="text-[11px] text-warn py-0.5">{c}</div>
          ))}
        </div>
      )}

      {activeFiles.length > 0 && (
        <div>
          <div className="wv-label mb-1">ACTIVE FILES</div>
          {activeFiles.slice(0, 8).map((f, i) => (
            <div key={i} className="text-[10px] font-mono text-text-tertiary py-0.5 truncate">{f}</div>
          ))}
        </div>
      )}

      {!project && !repo && (
        <p className="text-[11px] text-text-tertiary text-center py-4">No active context</p>
      )}
    </div>
  )
}

function ExecutionSection() {
  const s = useExecutionSummaryStore((st) => st.summary)

  const state = s.state
  const readyCount = s.ready_count
  const blockedCount = s.blocked_count
  const pendingApprovals = s.pending_approval_count
  const topBlockers = s.top_blockers
  const delegationCoverage = s.delegation_coverage

  const stateColor: Record<string, string> = {
    idle: 'text-text-tertiary', assessing: 'text-cyan', governed: 'text-ok',
    executing: 'text-ok', blocked: 'text-danger',
  }

  return (
    <div className="space-y-3">
      <div className="wv-label mb-2">EXECUTION STATE</div>
      <div className="flex items-center gap-2">
        <span className={clsx('text-[11px] font-mono uppercase', stateColor[state] || 'text-text-tertiary')}>{state}</span>
        <span className={clsx('text-[9px] font-mono uppercase', s.health === 'optimal' ? 'text-ok' : s.health === 'blocked' ? 'text-danger' : 'text-text-tertiary')}>{s.health}</span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div><div className="text-[14px] font-mono text-ok">{readyCount}</div><div className="text-[9px] text-text-tertiary">Ready</div></div>
        <div><div className="text-[14px] font-mono text-warn">{pendingApprovals}</div><div className="text-[9px] text-text-tertiary">Pending</div></div>
        <div><div className="text-[14px] font-mono text-danger">{blockedCount}</div><div className="text-[9px] text-text-tertiary">Blocked</div></div>
      </div>

      {delegationCoverage > 0 && (
        <div className="text-[11px]"><span className="text-text-tertiary">Delegation</span> <span className="text-text-primary">{Math.round(delegationCoverage * 100)}%</span></div>
      )}

      {topBlockers.length > 0 && (
        <div>
          <div className="wv-label mb-1">BLOCKERS</div>
          {topBlockers.slice(0, 5).map((b, i) => (
            <div key={i} className="text-[11px] text-danger py-0.5">{(b as Record<string, string>).description || JSON.stringify(b)}</div>
          ))}
        </div>
      )}

      {state === 'idle' && topBlockers.length === 0 && (
        <p className="text-[11px] text-text-tertiary text-center py-4">No active execution</p>
      )}
    </div>
  )
}
