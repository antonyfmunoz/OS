import { useKnowledgeStore } from '../stores/knowledgeStore'
import { usePolling } from '../hooks/usePolling'

const PRIMITIVE_COLORS: Record<string, string> = {
  state: 'var(--color-cyan)',
  change: 'var(--color-warn)',
  constraint: 'var(--color-danger)',
  resource: 'var(--color-ok)',
  signal: 'var(--color-violet)',
  action: 'var(--color-cyan)',
  outcome: 'var(--color-ok)',
  feedback: 'var(--color-warn)',
  goal: 'var(--color-violet)',
  time: 'var(--color-text-tertiary)',
}

const TABS = [
  { id: 'observations' as const, label: 'Observations' },
  { id: 'memory' as const, label: 'Memory' },
  { id: 'skills' as const, label: 'Skills' },
  { id: 'tracking' as const, label: 'Tracking' },
]

export function KnowledgePanel() {
  const observations = useKnowledgeStore((s) => s.observations)
  const memory = useKnowledgeStore((s) => s.memory)
  const skills = useKnowledgeStore((s) => s.skills)
  const tracking = useKnowledgeStore((s) => s.tracking)
  const viewMode = useKnowledgeStore((s) => s.viewMode)
  const searchQuery = useKnowledgeStore((s) => s.searchQuery)
  const selectedNode = useKnowledgeStore((s) => s.selectedNode)
  const setViewMode = useKnowledgeStore((s) => s.setViewMode)
  const setSearchQuery = useKnowledgeStore((s) => s.setSearchQuery)
  const selectNode = useKnowledgeStore((s) => s.selectNode)
  const fetchObservations = useKnowledgeStore((s) => s.fetchObservations)
  const fetchMemory = useKnowledgeStore((s) => s.fetchMemory)
  const fetchSkills = useKnowledgeStore((s) => s.fetchSkills)
  const fetchTracking = useKnowledgeStore((s) => s.fetchTracking)

  usePolling(() => {
    fetchObservations()
    fetchMemory()
    fetchSkills()
    fetchTracking()
  }, 10000)

  const q = searchQuery.toLowerCase()

  const filteredObs = q
    ? observations.filter((o) => o.label.toLowerCase().includes(q) || o.description.toLowerCase().includes(q))
    : observations

  const filteredMem = q
    ? memory.filter((m) => m.label.toLowerCase().includes(q) || m.description.toLowerCase().includes(q))
    : memory

  const filteredSkills = q
    ? skills.filter((s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q))
    : skills

  const filteredTracking = q
    ? tracking.filter((t) => t.name.toLowerCase().includes(q))
    : tracking

  return (
    <div className="flex h-full">
      {/* Main list */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Tab bar + search */}
        <div
          className="flex items-center gap-3 px-4 h-10 shrink-0"
          style={{ borderBottom: '1px solid var(--color-border)' }}
        >
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setViewMode(tab.id)}
              className="wv-label pb-2 transition-colors"
              style={{
                color: viewMode === tab.id ? 'var(--color-cyan)' : 'var(--color-text-secondary)',
                borderBottom: viewMode === tab.id ? '2px solid var(--color-cyan)' : '2px solid transparent',
              }}
            >
              {tab.label}
            </button>
          ))}

          <div className="flex-1" />

          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search..."
            className="text-xs px-2 py-1 rounded bg-transparent outline-none w-48"
            style={{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}
          />
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {viewMode === 'observations' && (
            <div className="space-y-1.5">
              {filteredObs.map((obs) => (
                <button
                  key={obs.id}
                  onClick={() => selectNode(obs)}
                  className="w-full text-left px-3 py-2 rounded transition-colors hover:bg-[var(--color-surface-raised)]"
                  style={{
                    background: selectedNode?.id === obs.id ? 'var(--color-surface-raised)' : 'transparent',
                    border: selectedNode?.id === obs.id ? '1px solid var(--color-border-active)' : '1px solid transparent',
                  }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ background: PRIMITIVE_COLORS[obs.primitive_type] || 'var(--color-text-tertiary)' }}
                    />
                    <span className="font-mono text-xs uppercase" style={{ color: PRIMITIVE_COLORS[obs.primitive_type] || 'var(--color-text-tertiary)' }}>
                      {obs.primitive_type}
                    </span>
                    <span className="text-xs truncate" style={{ color: 'var(--color-text-tertiary)' }}>
                      {obs.source_document}
                    </span>
                  </div>
                  <p className="text-sm truncate">{obs.label}</p>
                </button>
              ))}
              {filteredObs.length === 0 && (
                <p className="text-center text-xs py-8" style={{ color: 'var(--color-text-tertiary)' }}>
                  No observations found
                </p>
              )}
            </div>
          )}

          {viewMode === 'memory' && (
            <div className="space-y-1.5">
              {filteredMem.map((m) => (
                <div
                  key={m.id}
                  className="px-3 py-2 rounded"
                  style={{ background: 'var(--color-surface-raised)', border: '1px solid var(--color-border)' }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs" style={{ color: 'var(--color-cyan)' }}>
                      {m.memory_type}
                    </span>
                    <span className="font-mono text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                      {m.primitive_type}
                    </span>
                    {m.domain_id && (
                      <span className="font-mono text-xs" style={{ color: 'var(--color-violet)' }}>
                        {m.domain_id}
                      </span>
                    )}
                  </div>
                  <p className="text-sm">{m.label}</p>
                  <p className="text-xs mt-1 line-clamp-2" style={{ color: 'var(--color-text-secondary)' }}>
                    {m.description}
                  </p>
                </div>
              ))}
              {filteredMem.length === 0 && (
                <p className="text-center text-xs py-8" style={{ color: 'var(--color-text-tertiary)' }}>
                  No memory entries found
                </p>
              )}
            </div>
          )}

          {viewMode === 'skills' && (
            <div className="space-y-1.5">
              {filteredSkills.map((skill) => (
                <div
                  key={skill.id}
                  className="px-3 py-2 rounded"
                  style={{ background: 'var(--color-surface-raised)', border: '1px solid var(--color-border)' }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium" style={{ color: 'var(--color-cyan)' }}>
                      {skill.name}
                    </span>
                    <span className="font-mono text-xs px-1 rounded" style={{ color: 'var(--color-text-tertiary)', background: 'var(--color-surface-overlay)' }}>
                      {skill.trigger}
                    </span>
                    <span className="font-mono text-xs px-1 rounded" style={{ color: 'var(--color-text-tertiary)', background: 'var(--color-surface-overlay)' }}>
                      {skill.effort}
                    </span>
                  </div>
                  <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                    {skill.description}
                  </p>
                </div>
              ))}
              {filteredSkills.length === 0 && (
                <p className="text-center text-xs py-8" style={{ color: 'var(--color-text-tertiary)' }}>
                  No skills found
                </p>
              )}
            </div>
          )}

          {viewMode === 'tracking' && (
            <div className="space-y-1.5">
              {filteredTracking.map((t) => (
                <div
                  key={t.id}
                  className="flex items-center gap-3 px-3 py-2 rounded"
                  style={{ background: 'var(--color-surface-raised)', border: '1px solid var(--color-border)' }}
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: t.status === 'active' ? 'var(--color-ok)' : 'var(--color-text-tertiary)' }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate">{t.name}</p>
                    <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                      {t.change_count} changes · last {new Date(t.last_changed).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))}
              {filteredTracking.length === 0 && (
                <p className="text-center text-xs py-8" style={{ color: 'var(--color-text-tertiary)' }}>
                  No tracked documents
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Node inspector sidebar */}
      {selectedNode && (
        <div
          className="w-80 shrink-0 overflow-y-auto p-4"
          style={{ borderLeft: '1px solid var(--color-border)', background: 'var(--color-surface)' }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold">Node Inspector</h3>
            <button
              onClick={() => selectNode(null)}
              className="text-xs px-2 py-1 rounded"
              style={{ color: 'var(--color-text-tertiary)', border: '1px solid var(--color-border)' }}
            >
              close
            </button>
          </div>

          <div className="space-y-3">
            <div>
              <p className="wv-label mb-1">Label</p>
              <p className="text-sm">{selectedNode.label}</p>
            </div>
            <div>
              <p className="wv-label mb-1">Primitive</p>
              <span
                className="font-mono text-xs uppercase px-1.5 py-0.5 rounded"
                style={{
                  color: PRIMITIVE_COLORS[selectedNode.primitive_type] || 'var(--color-text-tertiary)',
                  background: `${PRIMITIVE_COLORS[selectedNode.primitive_type] || 'var(--color-text-tertiary)'}15`,
                }}
              >
                {selectedNode.primitive_type}
              </span>
            </div>
            <div>
              <p className="wv-label mb-1">Description</p>
              <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                {selectedNode.description || 'No description'}
              </p>
            </div>
            {selectedNode.evidence && (
              <div>
                <p className="wv-label mb-1">Evidence</p>
                <p className="text-xs font-mono p-2 rounded" style={{ color: 'var(--color-text-secondary)', background: 'var(--color-surface-raised)' }}>
                  {selectedNode.evidence}
                </p>
              </div>
            )}
            <div>
              <p className="wv-label mb-1">Source</p>
              <p className="text-xs font-mono" style={{ color: 'var(--color-cyan)' }}>
                {selectedNode.source_document || 'unknown'}
              </p>
            </div>
            {selectedNode.relationships.length > 0 && (
              <div>
                <p className="wv-label mb-1">Relationships</p>
                <div className="space-y-1">
                  {selectedNode.relationships.map((r, i) => (
                    <p key={i} className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                      <span style={{ color: 'var(--color-violet)' }}>{r.type}</span> → {r.target}
                    </p>
                  ))}
                </div>
              </div>
            )}
            <div>
              <p className="wv-label mb-1">Created</p>
              <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                {selectedNode.created_at ? new Date(selectedNode.created_at).toLocaleString() : 'unknown'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
