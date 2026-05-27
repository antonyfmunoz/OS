import { clsx } from 'clsx'
import { useState } from 'react'
import { ChevronLeft, ChevronRight, MessageSquare, Activity, Terminal } from 'lucide-react'
import { useSystemStore } from '../stores/systemStore'
import { usePolling } from '../hooks/usePolling'
import { relativeTime } from '../lib/time'

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

function ChatSection() {
  return (
    <div className="flex flex-col h-full">
      <div className="wv-label mb-2">DEX ASSISTANT</div>
      <div className="flex-1 flex items-center justify-center">
        <p className="text-[11px] text-text-tertiary text-center">
          AI chat interface<br />awaiting integration
        </p>
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
