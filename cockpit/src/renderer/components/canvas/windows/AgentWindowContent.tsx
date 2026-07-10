import { useState, useEffect } from 'react'
import { useAgentStore } from '../../../stores/agentStore'
import { fetchApi } from '../../../api/client'

interface Props {
  agentId?: string
  paused: boolean
}

type Tab = 'info' | 'terminal' | 'comms'

export function AgentWindowContent({ agentId, paused }: Props) {
  const agents = useAgentStore((s) => s.agents)
  const fetchAgents = useAgentStore((s) => s.fetchAgents)
  const [tab, setTab] = useState<Tab>('info')
  const [termOutput, setTermOutput] = useState('')

  const agent = agents.find((a) => a.id === agentId)

  useEffect(() => {
    if (agents.length === 0) fetchAgents()
  }, [agents.length, fetchAgents])

  useEffect(() => {
    if (tab !== 'terminal' || paused || !agent) return
    let active = true
    const sessionName = agent.name?.toLowerCase().replace(/\s+/g, '_') ?? 'assistant_main'
    const poll = async () => {
      try {
        const res = await fetchApi(`/tmux/capture/${sessionName}/0`)
        if (active && res.output) setTermOutput(res.output)
      } catch { /* silent */ }
    }
    poll()
    const id = setInterval(poll, 2000)
    return () => { active = false; clearInterval(id) }
  }, [tab, paused, agent])

  if (!agent) {
    return (
      <div className="flex items-center justify-center h-full" style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="text-[12px]">Agent not found</span>
      </div>
    )
  }

  const tabStyle = (t: Tab) => ({
    color: tab === t ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)',
    borderBottom: tab === t ? '2px solid var(--color-cyan)' : '2px solid transparent',
  })

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex gap-3 px-2 shrink-0" style={{ borderBottom: '1px solid var(--color-border)' }}>
        {(['info', 'terminal', 'comms'] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)} className="py-1 text-[11px] capitalize" style={tabStyle(t)}>
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-auto p-2">
        {tab === 'info' && (
          <div className="space-y-2 text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>
            <div><span style={{ color: 'var(--color-text-tertiary)' }}>Role:</span> {agent.role ?? 'agent'}</div>
            <div><span style={{ color: 'var(--color-text-tertiary)' }}>Status:</span> {agent.status}</div>
            {agent.skills && agent.skills.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {agent.skills.map((s) => (
                  <span key={s} className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)' }}>{s}</span>
                ))}
              </div>
            )}
            {agent.last_action && <div className="mt-2" style={{ color: 'var(--color-text-tertiary)' }}>{agent.last_action}</div>}
          </div>
        )}

        {tab === 'terminal' && (
          <pre className="text-[10px] leading-[1.4] whitespace-pre-wrap" style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
            {termOutput || (paused ? 'Paused' : 'Waiting for terminal output...')}
          </pre>
        )}

        {tab === 'comms' && (
          <div className="text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>
            A2A communication feed — connects via organism WebSocket
          </div>
        )}
      </div>
    </div>
  )
}
