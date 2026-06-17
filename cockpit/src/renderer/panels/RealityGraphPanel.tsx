import { useEffect, useState } from 'react'
import { Globe, RefreshCw, Search, ArrowRight, Check } from 'lucide-react'
import { useRealityGraphStore } from '../stores/realityGraphStore'

type Tab = 'overview' | 'entities' | 'resolve'

const TYPE_COLORS: Record<string, string> = {
  project: 'text-cyan',
  repository: 'text-green-400',
  workspace: 'text-purple-400',
  device: 'text-yellow-400',
  document: 'text-blue-400',
  service: 'text-orange-400',
  infrastructure: 'text-orange-400',
  projection: 'text-pink-400',
  capability: 'text-emerald-400',
  delegation_mission: 'text-red-400',
  approval: 'text-amber-400',
}

function TypeBadge({ type }: { type: string }) {
  const color = TYPE_COLORS[type] || 'text-text-secondary'
  return (
    <span className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-surface-secondary ${color}`}>
      {type.replace('_', ' ')}
    </span>
  )
}

function StatusDot({ status }: { status: string }) {
  const color = status === 'active' ? 'bg-green-400' : status === 'degraded' ? 'bg-yellow-400' : 'bg-text-tertiary'
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${color}`} />
}

export function RealityGraphPanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const [resolveInput, setResolveInput] = useState('')
  const [filterType, setFilterType] = useState('')
  const {
    summary, entities, selectedEntity, neighbors, resolvedContext, loading,
    fetchSummary, fetchEntities, fetchEntity, fetchNeighbors, resolveContext,
  } = useRealityGraphStore()

  useEffect(() => { fetchSummary() }, [])

  const refresh = () => {
    fetchSummary()
    if (tab === 'entities') fetchEntities(filterType || undefined)
  }

  const handleResolve = () => {
    if (resolveInput.trim()) resolveContext(resolveInput.trim())
  }

  const handleEntityClick = (entityId: string) => {
    fetchEntity(entityId)
    fetchNeighbors(entityId)
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <Globe size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Reality Graph</span>
          {summary && (
            <span className="text-[9px] font-mono text-text-tertiary">
              {summary.entity_count} entities · {summary.relation_count} edges
            </span>
          )}
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border shrink-0">
        {(['overview', 'entities', 'resolve'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t)
              if (t === 'entities') fetchEntities(filterType || undefined)
            }}
            className={`px-4 py-2 text-[10px] font-mono uppercase tracking-wider border-b-2 transition-colors ${
              tab === t ? 'border-cyan text-cyan' : 'border-transparent text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {tab === 'overview' && summary && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-surface-secondary rounded p-3">
                <div className="text-[9px] font-mono text-text-tertiary uppercase">Entities</div>
                <div className="text-2xl font-mono text-cyan">{summary.entity_count}</div>
              </div>
              <div className="bg-surface-secondary rounded p-3">
                <div className="text-[9px] font-mono text-text-tertiary uppercase">Relations</div>
                <div className="text-2xl font-mono text-cyan">{summary.relation_count}</div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-[10px] font-mono text-text-tertiary uppercase">By Type</div>
              {Object.entries(summary.entities_by_type).sort(([, a], [, b]) => b - a).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between bg-surface-secondary rounded px-3 py-2">
                  <TypeBadge type={type} />
                  <span className="text-[11px] font-mono text-text-primary">{count}</span>
                </div>
              ))}
            </div>

            <div className="space-y-2">
              <div className="text-[10px] font-mono text-text-tertiary uppercase">Edge Types</div>
              {Object.entries(summary.relations_by_type).sort(([, a], [, b]) => b - a).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between bg-surface-secondary rounded px-3 py-2">
                  <span className="text-[10px] font-mono text-text-secondary">{type.replace('_', ' ')}</span>
                  <span className="text-[11px] font-mono text-text-primary">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'entities' && (
          <div className="space-y-3">
            <div className="flex gap-2">
              <select
                value={filterType}
                onChange={(e) => {
                  setFilterType(e.target.value)
                  fetchEntities(e.target.value || undefined)
                }}
                className="bg-surface-secondary border border-border rounded px-2 py-1 text-[10px] font-mono text-text-primary"
              >
                <option value="">All Types</option>
                {summary && Object.keys(summary.entities_by_type).map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div className="flex gap-3">
              {/* Entity List */}
              <div className="flex-1 space-y-1">
                {entities.map((entity) => (
                  <button
                    key={entity.entity_id}
                    onClick={() => handleEntityClick(entity.entity_id)}
                    className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded transition-colors ${
                      selectedEntity?.entity_id === entity.entity_id
                        ? 'bg-cyan/10 border border-cyan/30'
                        : 'bg-surface-secondary hover:bg-surface-secondary/80'
                    }`}
                  >
                    <StatusDot status={entity.status} />
                    <span className="text-[11px] font-mono text-text-primary flex-1 truncate">{entity.name}</span>
                    <TypeBadge type={entity.entity_type} />
                  </button>
                ))}
                {entities.length === 0 && (
                  <div className="text-[10px] font-mono text-text-tertiary text-center py-8">No entities</div>
                )}
              </div>

              {/* Detail Panel */}
              {selectedEntity && (
                <div className="w-80 bg-surface-secondary rounded p-3 space-y-3">
                  <div className="flex items-center gap-2">
                    <StatusDot status={selectedEntity.status} />
                    <span className="text-[12px] font-mono text-text-primary font-medium">{selectedEntity.name}</span>
                  </div>
                  <TypeBadge type={selectedEntity.entity_type} />

                  <div className="space-y-1 text-[10px] font-mono">
                    <div className="text-text-tertiary">ID: {selectedEntity.entity_id}</div>
                    <div className="text-text-tertiary">Source: {selectedEntity.source_system}</div>
                    {Object.entries(selectedEntity.properties).map(([k, v]) => (
                      <div key={k} className="text-text-secondary">
                        <span className="text-text-tertiary">{k}:</span> {String(v)}
                      </div>
                    ))}
                  </div>

                  {neighbors.length > 0 && (
                    <div className="space-y-1">
                      <div className="text-[9px] font-mono text-text-tertiary uppercase">Neighbors</div>
                      {neighbors.map((n) => (
                        <button
                          key={n.entity_id}
                          onClick={() => handleEntityClick(n.entity_id)}
                          className="flex items-center gap-1.5 text-[10px] font-mono text-cyan hover:text-cyan/80"
                        >
                          <ArrowRight size={8} />
                          {n.name}
                          <TypeBadge type={n.entity_type} />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {tab === 'resolve' && (
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={resolveInput}
                onChange={(e) => setResolveInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleResolve()}
                placeholder="Use Clerk for CreatorOS..."
                className="flex-1 bg-surface-secondary border border-border rounded px-3 py-2 text-[11px] font-mono text-text-primary placeholder:text-text-tertiary"
              />
              <button
                onClick={handleResolve}
                disabled={loading || !resolveInput.trim()}
                className="flex items-center gap-1 px-3 py-2 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
              >
                <Search size={10} />
                Resolve
              </button>
            </div>

            {resolvedContext && (
              <div className="space-y-3">
                {/* Confidence */}
                <div className="flex items-center gap-2">
                  <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${
                    resolvedContext.confidence >= 0.7 ? 'bg-green-400/10 text-green-400'
                      : resolvedContext.confidence >= 0.4 ? 'bg-yellow-400/10 text-yellow-400'
                        : 'bg-red-400/10 text-red-400'
                  }`}>
                    {(resolvedContext.confidence * 100).toFixed(0)}% confidence
                  </span>
                  <span className="text-[9px] font-mono text-text-tertiary">{resolvedContext.strategy}</span>
                </div>

                {/* Resolved Fields */}
                <div className="bg-surface-secondary rounded p-3 space-y-2">
                  {resolvedContext.project_name && (
                    <div className="flex items-center gap-2 text-[11px] font-mono">
                      <Check size={10} className="text-green-400" />
                      <span className="text-text-tertiary w-20">Project</span>
                      <span className="text-text-primary">{resolvedContext.project_name}</span>
                    </div>
                  )}
                  {resolvedContext.repository_name && (
                    <div className="flex items-center gap-2 text-[11px] font-mono">
                      <Check size={10} className="text-green-400" />
                      <span className="text-text-tertiary w-20">Repo</span>
                      <span className="text-text-primary">{resolvedContext.repository_name}</span>
                    </div>
                  )}
                  {resolvedContext.workspace_name && (
                    <div className="flex items-center gap-2 text-[11px] font-mono">
                      <Check size={10} className="text-green-400" />
                      <span className="text-text-tertiary w-20">Workspace</span>
                      <span className="text-text-primary">{resolvedContext.workspace_name}</span>
                    </div>
                  )}
                  {resolvedContext.device_id && (
                    <div className="flex items-center gap-2 text-[11px] font-mono">
                      <Check size={10} className="text-green-400" />
                      <span className="text-text-tertiary w-20">Device</span>
                      <span className="text-text-primary">{resolvedContext.device_id}</span>
                    </div>
                  )}
                  {resolvedContext.projection && (
                    <div className="flex items-center gap-2 text-[11px] font-mono">
                      <Check size={10} className="text-green-400" />
                      <span className="text-text-tertiary w-20">Projection</span>
                      <span className="text-text-primary">{resolvedContext.projection}</span>
                    </div>
                  )}
                </div>

                {/* Unresolved */}
                {resolvedContext.unresolved_references.length > 0 && (
                  <div className="bg-surface-secondary rounded p-3 space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Unresolved</div>
                    {resolvedContext.unresolved_references.map((ref, i) => (
                      <div key={i} className="text-[10px] font-mono text-yellow-400">? {ref}</div>
                    ))}
                  </div>
                )}

                {/* Resolution Chain */}
                {resolvedContext.resolution_chain.length > 0 && (
                  <div className="bg-surface-secondary rounded p-3 space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Resolution Chain</div>
                    {resolvedContext.resolution_chain.map((step, i) => (
                      <div key={i} className="text-[10px] font-mono text-text-secondary">
                        {i + 1}. {step.step}
                        {step.candidate && <span className="text-text-tertiary"> ({step.candidate})</span>}
                        {step.resolved_to && <span className="text-cyan"> → {step.resolved_to}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
