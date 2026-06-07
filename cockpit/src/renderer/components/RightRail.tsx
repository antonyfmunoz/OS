import { clsx } from 'clsx'
import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { ChevronLeft, ChevronRight, MessageSquare, Activity, Terminal, Send, Pencil, Check, Mic, MicOff } from 'lucide-react'
import { useSystemStore } from '../stores/systemStore'
import { useChatStore } from '../stores/chatStore'
import { useApprovalStore } from '../stores/approvalStore'
import { usePolling } from '../hooks/usePolling'
import { relativeTime } from '../lib/time'
import { useConfigStore } from '../stores/configStore'
import { useViewContextStore } from '../stores/viewContextStore'
import { useVoiceStore } from '../stores/voiceStore'
import { startVoice, stopVoice } from '../api/voice-controller'
import { fetchApi } from '../api/client'
import { useCockpitStore } from '../stores/cockpitStore'
import { normalizeLegacyMessage } from '../lib/rrip-normalize'
import { RRIPRenderer } from './cards/RRIPRenderer'
import type { RRIPSuggestedAction, RRIPMessage } from '../types/rrip'

type RightTab = 'chat' | 'activity' | 'logs'

export function RightRail() {
  const [collapsed, setCollapsed] = useState(false)
  const [activeTab, setActiveTab] = useState<RightTab>('chat')
  const traces = useSystemStore((s) => s.traces)
  const fetchTraces = useSystemStore((s) => s.fetchTraces)

  usePolling(fetchTraces, 5000, true, 750)

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
    <div className="flex flex-col w-[280px] bg-surface border-l border-border">
      {/* Tab bar — mirrored from LeftRail: collapse on inner edge, tabs on outer (right) edge */}
      <div className="flex items-center border-b border-border px-2 h-9 shrink-0">
        <button onClick={() => setCollapsed(true)} className="p-1 text-text-tertiary hover:text-cyan transition-colors shrink-0">
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
                  'flex items-center gap-2 px-2 py-1 text-[10px] font-mono uppercase tracking-wider leading-none transition-colors',
                  activeTab === t.id ? 'text-cyan' : 'text-text-tertiary hover:text-text-secondary',
                )}
              >
                <Icon size={14} />
                {t.label}
              </button>
            )
          })}
        </div>
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
  const approvals = useApprovalStore((s) => s.approvals)
  const approveAction = useApprovalStore((s) => s.approve)
  const denyAction = useApprovalStore((s) => s.deny)
  const scrollRef = useRef<HTMLDivElement>(null)
  const displayName = `${aiName} ASSISTANT`
  const [editingName, setEditingName] = useState(false)
  const [nameInput, setNameInput] = useState(aiName)
  const nameRef = useRef<HTMLInputElement>(null)
  const [voiceAvailable, setVoiceAvailable] = useState(true)

  const rripMessages = useMemo(() => {
    const normalized = messages.map(normalizeLegacyMessage)
    const pendingApprovals: RRIPMessage[] = approvals
      .filter((a) => a.status === 'pending')
      .map((a) => ({
        id: `approval-${a.id}`,
        role: 'system' as const,
        kind: 'approval_request' as const,
        content: a.description,
        timestamp: a.created_at,
        approval_data: {
          approval_id: a.id,
          description: a.description,
          risk_level: a.risk_level,
          agent: a.agent,
          status: a.status,
          created_at: a.created_at,
        },
      }))
    return [...normalized, ...pendingApprovals].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    )
  }, [messages, approvals])

  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight) }, [rripMessages])
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
      startVoice().catch(() => setVoiceAvailable(false))
    } else {
      stopVoice()
    }
  }, [micState])

  const handleSuggestedAction = useCallback((action: RRIPSuggestedAction) => {
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
      default:
        break
    }
  }, [sendMessage, viewContext, setPanel])

  const handleApprove = useCallback((approvalId: string) => {
    approveAction(approvalId)
  }, [approveAction])

  const handleDeny = useCallback((approvalId: string) => {
    denyAction(approvalId)
  }, [denyAction])

  const commitName = () => {
    const trimmed = nameInput.trim()
    if (trimmed && trimmed !== aiName) {
      setConfigValue('ai_name', trimmed)
    }
    if (!trimmed) setNameInput(aiName)
    setEditingName(false)
  }

  const voiceLabel = micState === 'listening' ? 'Listening...'
    : micState === 'processing' ? 'Transcribing...'
    : ttsState === 'speaking' ? 'Speaking...'
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
        {rripMessages.map((m) => (
          <RRIPRenderer
            key={m.id}
            message={m}
            aiName={aiName}
            onAction={handleSuggestedAction}
            onApprove={handleApprove}
            onDeny={handleDeny}
          />
        ))}
        {sending && (
          <div className="px-2 py-1.5 rounded text-[11px] bg-surface-raised text-text-tertiary mr-4 animate-pulse">
            {aiName} is thinking...
          </div>
        )}
        {rripMessages.length === 0 && !sending && (
          <p className="text-[11px] text-text-tertiary text-center py-4">Ask {aiName} anything</p>
        )}
      </div>
      <div className="flex flex-col gap-1 border-t border-border pt-2">
        {voiceLabel && (
          <div className="text-[9px] font-mono text-cyan animate-pulse px-1">{voiceLabel}</div>
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
            disabled={!voiceAvailable}
            className={clsx(
              'p-1.5 rounded transition-colors',
              !voiceAvailable ? 'text-text-tertiary opacity-30 cursor-not-allowed' :
              micState === 'listening' ? 'text-danger bg-danger/10' :
              'text-text-tertiary hover:text-cyan',
            )}
            title={!voiceAvailable ? 'Voice requires desktop app or HTTPS' : micState === 'listening' ? 'Stop listening' : 'Voice input'}
          >
            {micState === 'listening' ? <MicOff size={12} /> : <Mic size={12} />}
          </button>
          <button onClick={handleSend} disabled={sending || !input.trim()} className="p-1.5 rounded text-cyan hover:bg-cyan-glow transition-colors disabled:opacity-30">
            <Send size={12} />
          </button>
        </div>
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
          <div key={t.id} className={clsx('py-1', t.status === 'failed' ? 'text-danger' : 'text-text-secondary')}>
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
