import { useAgentStore } from '../stores/agentStore'
import { usePolling } from '../hooks/usePolling'

function StatusDot({ status }: { status: string }) {
  const colorClass = {
    active: 'bg-ok',
    idle: 'bg-warn',
    running: 'bg-ok',
    error: 'bg-danger',
    stopped: 'bg-text-tertiary',
  }[status] || 'bg-text-tertiary'

  return <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${colorClass}`} />
}

export function AgentsPanel() {
  const agents = useAgentStore((s) => s.agents)
  const selectedId = useAgentStore((s) => s.selectedId)
  const detail = useAgentStore((s) => s.detail)
  const fetchAgents = useAgentStore((s) => s.fetchAgents)
  const selectAgent = useAgentStore((s) => s.selectAgent)
  const controlAgent = useAgentStore((s) => s.controlAgent)

  usePolling(fetchAgents, 5000)

  return (
    <div className="flex h-full">
      {/* Fleet sidebar */}
      <div className="w-56 shrink-0 overflow-y-auto border-r border-border">
        <div className="px-3 py-2">
          <h3 className="wv-label">Fleet — {agents.length} agents</h3>
        </div>
        {agents.map((agent) => (
          <button
            key={agent.id}
            onClick={() => selectAgent(agent.id)}
            className="w-full flex items-center gap-2 px-3 py-2 text-left transition-colors"
            style={{
              background: selectedId === agent.id ? 'var(--color-surface-raised)' : 'transparent',
              borderLeft: selectedId === agent.id ? '2px solid var(--color-cyan)' : '2px solid transparent',
            }}
          >
            <StatusDot status={agent.status} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-text-primary truncate">{agent.name}</p>
              <p className="text-xs text-text-tertiary truncate">{agent.role}</p>
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
            <p className="text-sm text-text-tertiary">Select an agent to view details</p>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <StatusDot status={detail.status} />
              <h2 className="text-lg font-semibold">{detail.name}</h2>
              <span className="wv-label">{detail.status}</span>
            </div>

            {/* Controls */}
            <div className="flex gap-2 mb-6">
              <button
                onClick={() => controlAgent('start', detail.id)}
                className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-cyan-glow text-cyan border border-border transition-colors"
              >
                start
              </button>
              <button
                onClick={() => controlAgent('stop', detail.id)}
                className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-surface-raised text-danger border border-border transition-colors"
              >
                stop
              </button>
              <button
                onClick={() => controlAgent('restart', detail.id)}
                className="px-3 py-1.5 text-xs font-mono uppercase rounded bg-surface-raised text-warn border border-border transition-colors"
              >
                restart
              </button>
            </div>

            {/* Skills */}
            <section className="mb-4">
              <h3 className="wv-label mb-2">Skills</h3>
              <div className="flex flex-wrap gap-1.5">
                {detail.skills.map((skill) => (
                  <span key={skill} className="px-2 py-0.5 text-xs rounded bg-surface-raised text-text-secondary border border-border">
                    {skill}
                  </span>
                ))}
              </div>
            </section>

            {/* Proof of work */}
            <section>
              <h3 className="wv-label mb-2">Proof of Work — {detail.deliverables.length} deliverables</h3>
              <div className="space-y-2">
                {detail.deliverables.map((d) => (
                  <div key={d.id} className="wv-card px-3 py-2">
                    <p className="text-sm">{d.description}</p>
                    <p className="text-xs mt-1 text-text-tertiary">
                      {new Date(d.created_at).toLocaleDateString()} · {d.status}
                    </p>
                  </div>
                ))}
                {detail.deliverables.length === 0 && (
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
