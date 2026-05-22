import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import type { AgentResponse } from '../api/client.ts'

type TierFilter = AgentResponse['tier'] | 'all'
type StatusFilterType = AgentResponse['status'] | 'all'

const STATUS_COLOR: Record<AgentResponse['status'], string> = {
  active: 'bg-ok',
  idle: 'bg-warn',
  offline: 'bg-border',
}

const STATUS_BADGE: Record<AgentResponse['status'], string> = {
  active: 'wv-badge-ok',
  idle: 'wv-badge-warn',
  offline: 'wv-badge-danger',
}

const TIER_BADGE: Record<AgentResponse['tier'], string> = {
  strategic: 'wv-badge-violet',
  operational: 'wv-badge-cyan',
  tactical: 'wv-badge-warn',
}

function StatsBar({ agents }: { agents: AgentResponse[] }) {
  const active = agents.filter((a) => a.status === 'active').length
  const idle = agents.filter((a) => a.status === 'idle').length
  const offline = agents.filter((a) => a.status === 'offline').length
  const totalTasks = agents.reduce((s, a) => s + a.tasks_completed, 0)

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-ok">{active}</div>
        <div className="wv-label mt-1">ACTIVE</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-warn">{idle}</div>
        <div className="wv-label mt-1">IDLE</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-text-tertiary">{offline}</div>
        <div className="wv-label mt-1">OFFLINE</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-cyan">{totalTasks}</div>
        <div className="wv-label mt-1">TOTAL TASKS</div>
      </div>
    </div>
  )
}

function AgentCard({ agent, selected, onClick }: { agent: AgentResponse; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={clsx('w-full text-left wv-card p-4 transition-colors', selected && 'ring-1 ring-cyan')}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={clsx('w-2 h-2 rounded-full', STATUS_COLOR[agent.status])} />
          <span className="text-[12px] text-text-primary font-mono">{agent.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={clsx('wv-badge', TIER_BADGE[agent.tier])}>{agent.tier}</span>
          <span className="text-[9px] text-text-tertiary font-mono uppercase">{agent.model}</span>
        </div>
      </div>
      <div className="text-[11px] text-text-secondary mb-2">{agent.role}</div>
      <div className="flex items-center justify-between text-[10px] text-text-tertiary">
        <span>{agent.tasks_completed} tasks</span>
        <span>{relativeTime(agent.last_active)}</span>
      </div>
    </button>
  )
}

function DetailPanel({ agent, onClose }: { agent: AgentResponse; onClose: () => void }) {
  const [signalInput, setSignalInput] = useState('')
  const [sending, setSending] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)

  const handleSignal = async () => {
    if (!signalInput.trim() || sending) return
    setSending(true)
    try {
      const { api } = await import('../api/client.ts')
      const res = await api.agentSignal(agent.id, signalInput.trim())
      setFeedback(`Delegated to ${res.delegated_to}`)
      setSignalInput('')
      useCockpitStore.getState().fetchAll()
    } catch {
      setFeedback('Signal failed')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="w-96 border-l border-border flex flex-col bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <span className="wv-label">AGENT DETAIL</span>
        <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-[14px] transition-colors">✕</button>
      </div>
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div className="flex items-center gap-3">
          <span className={clsx('w-3 h-3 rounded-full', STATUS_COLOR[agent.status])} />
          <span className="text-[14px] text-text-primary font-mono">{agent.name}</span>
        </div>
        <div>
          <div className="wv-label mb-1">ROLE</div>
          <div className="text-[11px] text-text-secondary">{agent.role}</div>
        </div>
        <div className="flex gap-4">
          <div>
            <div className="wv-label mb-1">STATUS</div>
            <span className={clsx('wv-badge', STATUS_BADGE[agent.status])}>{agent.status}</span>
          </div>
          <div>
            <div className="wv-label mb-1">TIER</div>
            <span className={clsx('wv-badge', TIER_BADGE[agent.tier])}>{agent.tier}</span>
          </div>
          <div>
            <div className="wv-label mb-1">MODEL</div>
            <span className="text-[11px] text-cyan font-mono">{agent.model}</span>
          </div>
        </div>
        <div>
          <div className="wv-label mb-1">LAST ACTIVE</div>
          <div className="text-[11px] text-text-secondary">{new Date(agent.last_active).toLocaleString()}</div>
        </div>
        <div>
          <div className="wv-label mb-1">TASKS COMPLETED</div>
          <div className="wv-metric text-text-primary">{agent.tasks_completed}</div>
        </div>
        <div>
          <div className="wv-label mb-2">CAPABILITIES</div>
          <div className="flex flex-wrap gap-1.5">
            {agent.capabilities.length > 0 ? agent.capabilities.map((c) => (
              <span key={c} className="wv-badge wv-badge-cyan">{c}</span>
            )) : <span className="text-[10px] text-text-tertiary">No capabilities listed</span>}
          </div>
        </div>
        <div className="border-t border-border pt-4">
          <div className="wv-label mb-2">SEND SIGNAL</div>
          <div className="flex gap-2">
            <input type="text" value={signalInput} onChange={(e) => setSignalInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSignal()} placeholder="Task for this agent..." className="flex-1 bg-surface border border-border text-text-primary text-[11px] font-mono px-2 py-1 placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none" />
            <button onClick={handleSignal} disabled={sending || !signalInput.trim()} className="px-2 py-1 text-[9px] font-mono uppercase tracking-wider bg-cyan/10 text-cyan border border-cyan-dim hover:bg-cyan/20 transition-colors disabled:opacity-40">{sending ? '...' : 'Go'}</button>
          </div>
          {feedback && <div className="text-[10px] text-text-tertiary mt-1">{feedback}</div>}
        </div>
      </div>
    </div>
  )
}

export function Agents() {
  const { agents } = useCockpitStore()
  const [tierFilter, setTierFilter] = useState<TierFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilterType>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    return agents.filter((a) => {
      if (tierFilter !== 'all' && a.tier !== tierFilter) return false
      if (statusFilter !== 'all' && a.status !== statusFilter) return false
      return true
    })
  }, [agents, tierFilter, statusFilter])

  const selectedAgent = agents.find((a) => a.id === selectedId) ?? null

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">Agents</h1>
        <span className="text-[10px] font-mono text-text-tertiary uppercase">{agents.length} registered</span>
      </div>
      <StatsBar agents={agents} />
      <div className="flex items-center gap-4 mb-4">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-tertiary font-mono uppercase">Tier:</span>
          <div className="flex gap-1">
            {(['all', 'strategic', 'operational', 'tactical'] as const).map((t) => (
              <button key={t} onClick={() => setTierFilter(t)} className={clsx('px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors', tierFilter === t ? 'text-cyan bg-cyan-glow border-cyan-dim' : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active')}>{t}</button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-tertiary font-mono uppercase">Status:</span>
          <div className="flex gap-1">
            {(['all', 'active', 'idle', 'offline'] as const).map((s) => (
              <button key={s} onClick={() => setStatusFilter(s)} className={clsx('px-2 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors', statusFilter === s ? 'text-cyan bg-cyan-glow border-cyan-dim' : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active')}>{s}</button>
            ))}
          </div>
        </div>
      </div>
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 overflow-y-auto">
          <div className="grid grid-cols-2 gap-3">
            {filtered.length === 0 && <div className="col-span-2 text-center text-text-tertiary text-[11px] py-12">No agents matching current filters</div>}
            {filtered.map((agent) => (
              <AgentCard key={agent.id} agent={agent} selected={agent.id === selectedId} onClick={() => setSelectedId(agent.id === selectedId ? null : agent.id)} />
            ))}
          </div>
        </div>
        {selectedAgent && <DetailPanel agent={selectedAgent} onClose={() => setSelectedId(null)} />}
      </div>
    </div>
  )
}
