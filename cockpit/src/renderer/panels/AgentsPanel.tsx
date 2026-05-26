import { useAgentStore } from '../stores/agentStore'
import { usePolling } from '../hooks/usePolling'

function StatusDot({ status }: { status: string }) {
  const color = {
    active: 'var(--color-ok)',
    idle: 'var(--color-warn)',
    running: 'var(--color-ok)',
    error: 'var(--color-danger)',
    stopped: 'var(--color-text-tertiary)',
  }[status] || 'var(--color-text-tertiary)'

  return (
    <span
      className="inline-block w-2 h-2 rounded-full shrink-0"
      style={{ background: color }}
    />
  )
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
      <div
        className="w-56 shrink-0 overflow-y-auto"
        style={{ borderRight: '1px solid var(--color-border)' }}
      >
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
              <p className="text-sm truncate" style={{ color: 'var(--color-text-primary)' }}>
                {agent.name}
              </p>
              <p className="text-xs truncate" style={{ color: 'var(--color-text-tertiary)' }}>
                {agent.role}
              </p>
            </div>
          </button>
        ))}
        {agents.length === 0 && (
          <p className="px-3 py-4 text-xs text-center" style={{ color: 'var(--color-text-tertiary)' }}>
            No agents registered
          </p>
        )}
      </div>

      {/* Detail panel */}
      <div className="flex-1 overflow-y-auto p-4">
        {!detail ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm" style={{ color: 'var(--color-text-tertiary)' }}>
              Select an agent to view details
            </p>
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
                className="px-3 py-1.5 text-xs font-mono uppercase rounded transition-colors"
                style={{ background: 'var(--color-cyan-glow)', color: 'var(--color-cyan)', border: '1px solid var(--color-border)' }}
              >
                start
              </button>
              <button
                onClick={() => controlAgent('stop', detail.id)}
                className="px-3 py-1.5 text-xs font-mono uppercase rounded transition-colors"
                style={{ background: 'var(--color-surface-raised)', color: 'var(--color-danger)', border: '1px solid var(--color-border)' }}
              >
                stop
              </button>
              <button
                onClick={() => controlAgent('restart', detail.id)}
                className="px-3 py-1.5 text-xs font-mono uppercase rounded transition-colors"
                style={{ background: 'var(--color-surface-raised)', color: 'var(--color-warn)', border: '1px solid var(--color-border)' }}
              >
                restart
              </button>
            </div>

            {/* Skills */}
            <section className="mb-4">
              <h3 className="wv-label mb-2">Skills</h3>
              <div className="flex flex-wrap gap-1.5">
                {detail.skills.map((skill) => (
                  <span
                    key={skill}
                    className="px-2 py-0.5 text-xs rounded"
                    style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}
                  >
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
                  <div
                    key={d.id}
                    className="px-3 py-2 rounded"
                    style={{ background: 'var(--color-surface-raised)', border: '1px solid var(--color-border)' }}
                  >
                    <p className="text-sm">{d.description}</p>
                    <p className="text-xs mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
                      {new Date(d.created_at).toLocaleDateString()} · {d.status}
                    </p>
                  </div>
                ))}
                {detail.deliverables.length === 0 && (
                  <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>No deliverables yet</p>
                )}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
