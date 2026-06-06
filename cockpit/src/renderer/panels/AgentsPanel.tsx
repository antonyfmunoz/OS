import { useState } from 'react'
import { useAgentStore } from '../stores/agentStore'
import { useViewContextStore } from '../stores/viewContextStore'
import { usePolling } from '../hooks/usePolling'

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  active: { color: 'bg-ok', label: 'Active' },
  idle: { color: 'bg-warn', label: 'Idle' },
  running: { color: 'bg-ok', label: 'Running' },
  error: { color: 'bg-danger', label: 'Error' },
  stopped: { color: 'bg-text-tertiary', label: 'Stopped' },
  blocked: { color: 'bg-warn', label: 'Blocked' },
  completed: { color: 'bg-ok', label: 'Completed' },
}

function StatusDot({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || { color: 'bg-text-tertiary', label: status }
  return <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${cfg.color}`} title={cfg.label} />
}

export function AgentsPanel() {
  const agents = useAgentStore((s) => s.agents)
  const selectedId = useAgentStore((s) => s.selectedId)
  const detail = useAgentStore((s) => s.detail)
  const fetchAgents = useAgentStore((s) => s.fetchAgents)
  const selectAgent = useAgentStore((s) => s.selectAgent)
  const controlAgent = useAgentStore((s) => s.controlAgent)
  const handoff = useAgentStore((s) => s.handoff)

  const setViewContext = useViewContextStore((s) => s.setContext)

  const [signalText, setSignalText] = useState('')
  const [handoffTarget, setHandoffTarget] = useState('')
  const [handoffTask, setHandoffTask] = useState('')
  const [showHandoff, setShowHandoff] = useState(false)

  usePolling(fetchAgents, 5000)

  const sendSignal = async () => {
    if (!signalText.trim() || !detail) return
    const { sendSignal } = useAgentStore.getState()
    await sendSignal(detail.id, signalText)
    setSignalText('')
  }

  const doHandoff = async () => {
    if (!detail || !handoffTarget || !handoffTask) return
    await handoff(detail.id, handoffTarget, handoffTask)
    setShowHandoff(false)
    setHandoffTarget('')
    setHandoffTask('')
  }

  return (
    <div className="flex h-full">
      {/* Fleet sidebar */}
      <div className="w-64 shrink-0 overflow-y-auto border-r border-border">
        <div className="px-3 py-2 flex items-center justify-between">
          <h3 className="wv-label">Agent Fleet — {agents.length}</h3>
        </div>
        {agents.map((agent) => (
          <button
            key={agent.id}
            onClick={() => {
              selectAgent(agent.id)
              setViewContext({ selected_object_type: 'agent', selected_object_id: agent.id, selected_object_summary: agent.role || agent.name })
            }}
            className="w-full flex items-center gap-2 px-3 py-2 text-left transition-colors"
            style={{
              background: selectedId === agent.id ? 'var(--color-surface-raised)' : 'transparent',
              borderLeft: selectedId === agent.id ? '2px solid var(--color-cyan)' : '2px solid transparent',
            }}
          >
            <StatusDot status={agent.status} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-text-primary truncate">{agent.name}</p>
              <div className="flex items-center gap-2">
                <p className="text-xs text-text-tertiary truncate">{agent.role}</p>
                <span className={`text-[10px] font-mono ${STATUS_CONFIG[agent.status]?.color?.replace('bg-', 'text-') || 'text-text-tertiary'}`}>
                  {agent.status}
                </span>
              </div>
              {agent.last_active && (
                <p className="text-[10px] text-text-tertiary">{agent.last_active}</p>
              )}
            </div>
          </button>
        ))}
        {agents.length === 0 && (
          <p className="px-3 py-4 text-xs text-center text-text-tertiary">No agents registered</p>
        )}
      </div>

      {/* Detail panel */}
      <div className="flex-1 overflow-y-auto p-4">
        {!detail ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-text-tertiary">Select an agent to inspect, control, or reassign</p>
          </div>
        ) : (
          <div className="max-w-2xl">
            <div className="flex items-center gap-3 mb-4">
              <StatusDot status={detail.status} />
              <h2 className="text-lg font-semibold">{detail.name}</h2>
              <span className="wv-label">{detail.status}</span>
              <span className="text-xs text-text-tertiary font-mono">{detail.role}</span>
            </div>
            {detail?.capabilities && (
              <div className="flex flex-wrap gap-1 mt-1">
                {(Array.isArray(detail.capabilities) ? detail.capabilities : []).map((cap: string) => (
                  <span key={cap} className="text-[8px] font-mono px-1 py-0.5 rounded bg-surface-raised text-text-secondary border border-border">
                    {cap}
                  </span>
                ))}
              </div>
            )}
            {detail?.runtime_class && (
              <span className="text-[9px] font-mono text-text-tertiary mt-1 inline-block">
                runtime: {detail.runtime_class}
              </span>
            )}

            {/* Primary controls */}
            <div className="flex gap-2 mb-4">
              <button onClick={() => controlAgent('start', detail.id)}
                className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-cyan-glow text-cyan border border-border">
                resume
              </button>
              <button onClick={() => controlAgent('pause', detail.id)}
                className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-surface-raised text-warn border border-border">
                pause
              </button>
              <button onClick={() => controlAgent('stop', detail.id)}
                className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-surface-raised text-danger border border-border">
                stop
              </button>
              <button onClick={() => controlAgent('restart', detail.id)}
                className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-surface-raised text-text-secondary border border-border">
                restart
              </button>
              <button onClick={() => setShowHandoff(!showHandoff)}
                className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-surface-raised text-violet border border-border">
                handoff
              </button>
            </div>

            {/* Signal/message input */}
            <div className="flex gap-2 mb-6">
              <input value={signalText} onChange={(e) => setSignalText(e.target.value)}
                placeholder="Send signal/command to agent..."
                className="flex-1 px-3 py-1.5 text-xs rounded bg-surface border border-border text-text-primary outline-none"
                onKeyDown={(e) => e.key === 'Enter' && sendSignal()}
              />
              <button onClick={sendSignal}
                className="px-3 py-1.5 text-xs rounded bg-surface-raised text-cyan border border-border">
                Send
              </button>
            </div>

            {/* Handoff form */}
            {showHandoff && (
              <div className="border border-border rounded p-3 mb-4 bg-surface-secondary space-y-2">
                <p className="text-xs font-semibold text-text-secondary">Handoff Task to Another Agent</p>
                <input value={handoffTarget} onChange={(e) => setHandoffTarget(e.target.value)}
                  placeholder="Target agent ID or name"
                  className="w-full px-2 py-1 text-xs rounded bg-surface border border-border text-text-primary outline-none" />
                <input value={handoffTask} onChange={(e) => setHandoffTask(e.target.value)}
                  placeholder="Task description"
                  className="w-full px-2 py-1 text-xs rounded bg-surface border border-border text-text-primary outline-none" />
                <div className="flex gap-2">
                  <button onClick={doHandoff}
                    className="px-2 py-1 text-xs rounded text-violet border border-border">Execute Handoff</button>
                  <button onClick={() => setShowHandoff(false)}
                    className="px-2 py-1 text-xs rounded text-text-secondary border border-border">Cancel</button>
                </div>
              </div>
            )}

            {/* Skills */}
            <section className="mb-4">
              <h3 className="wv-label mb-2">Capabilities / Skills</h3>
              <div className="flex flex-wrap gap-1.5">
                {(detail.skills ?? []).map((skill) => (
                  <span key={skill} className="px-2 py-0.5 text-xs rounded bg-surface-raised text-text-secondary border border-border">
                    {skill}
                  </span>
                ))}
                {(detail.skills ?? []).length === 0 && (
                  <span className="text-xs text-text-tertiary">No skills registered</span>
                )}
              </div>
            </section>

            {/* Proof of work */}
            <section>
              <h3 className="wv-label mb-2">Proof of Work — {(detail.deliverables ?? []).length} deliverables</h3>
              <div className="space-y-2">
                {(detail.deliverables ?? []).map((d) => (
                  <div key={d.id} className="wv-card px-3 py-2">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm text-text-primary">{d.description}</p>
                      <span className={`text-[10px] font-mono ${d.status === 'completed' ? 'text-ok' : 'text-text-tertiary'}`}>
                        {d.status}
                      </span>
                    </div>
                    <p className="text-xs text-text-tertiary">
                      {new Date(d.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
                {(detail.deliverables ?? []).length === 0 && (
                  <p className="text-xs text-text-tertiary">No deliverables yet</p>
                )}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
