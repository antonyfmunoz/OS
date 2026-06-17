import { useEffect, useState } from 'react'
import { Globe, RefreshCw, Search, ArrowRight, Check, FileText, BookOpen, Activity, Brain, Archive } from 'lucide-react'
import { useRealityGraphStore } from '../stores/realityGraphStore'

type Tab = 'overview' | 'entities' | 'resolve' | 'artifacts' | 'files' | 'docs' | 'runtime' | 'knowledge'

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
    artifacts, repoSnapshot, docsSnapshot, runtimeSnapshot, knowledgeSnapshot,
    fetchSummary, fetchEntities, fetchEntity, fetchNeighbors, resolveContext,
    fetchArtifacts, fetchRepoSnapshot, fetchDocsSnapshot, fetchRuntimeSnapshot, fetchKnowledgeSnapshot,
  } = useRealityGraphStore()

  useEffect(() => { fetchSummary() }, [])

  const refresh = () => {
    fetchSummary()
    if (tab === 'entities') fetchEntities(filterType || undefined)
    if (tab === 'artifacts') fetchArtifacts()
    if (tab === 'files') fetchRepoSnapshot()
    if (tab === 'docs') fetchDocsSnapshot()
    if (tab === 'runtime') fetchRuntimeSnapshot()
    if (tab === 'knowledge') fetchKnowledgeSnapshot()
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
      <div className="flex border-b border-border shrink-0 overflow-x-auto">
        {(['overview', 'entities', 'resolve', 'artifacts', 'files', 'docs', 'runtime', 'knowledge'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t)
              if (t === 'entities') fetchEntities(filterType || undefined)
              if (t === 'artifacts') fetchArtifacts()
              if (t === 'files') fetchRepoSnapshot()
              if (t === 'docs') fetchDocsSnapshot()
              if (t === 'runtime') fetchRuntimeSnapshot()
              if (t === 'knowledge') fetchKnowledgeSnapshot()
            }}
            className={`px-3 py-2 text-[10px] font-mono uppercase tracking-wider border-b-2 transition-colors whitespace-nowrap ${
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

                {/* C6 Operational Fields */}
                {resolvedContext.files && resolvedContext.files.length > 0 && (
                  <div className="bg-surface-secondary rounded p-3 space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Files ({resolvedContext.files.length})</div>
                    {resolvedContext.files.slice(0, 10).map((f, i) => (
                      <div key={i} className="text-[10px] font-mono text-text-secondary">
                        <FileText size={8} className="inline mr-1 text-text-tertiary" />
                        {String(f.path || f.name || JSON.stringify(f))}
                        {f.category && <span className="text-text-tertiary ml-1">({String(f.category)})</span>}
                      </div>
                    ))}
                  </div>
                )}

                {resolvedContext.decisions && resolvedContext.decisions.length > 0 && (
                  <div className="bg-surface-secondary rounded p-3 space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Decisions ({resolvedContext.decisions.length})</div>
                    {resolvedContext.decisions.map((d, i) => (
                      <div key={i} className="text-[10px] font-mono text-text-secondary">
                        <Check size={8} className="inline mr-1 text-green-400" />
                        {String(d.summary || d.source_doc || JSON.stringify(d))}
                      </div>
                    ))}
                  </div>
                )}

                {resolvedContext.active_work && resolvedContext.active_work.length > 0 && (
                  <div className="bg-surface-secondary rounded p-3 space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Active Work ({resolvedContext.active_work.length})</div>
                    {resolvedContext.active_work.map((w, i) => (
                      <div key={i} className="text-[10px] font-mono text-text-secondary">
                        <Activity size={8} className="inline mr-1 text-yellow-400" />
                        {String(w.description || w.packet_id || JSON.stringify(w))}
                        {w.status && <span className="text-text-tertiary ml-1">[{String(w.status)}]</span>}
                      </div>
                    ))}
                  </div>
                )}

                {resolvedContext.constraints && resolvedContext.constraints.length > 0 && (
                  <div className="bg-surface-secondary rounded p-3 space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Constraints ({resolvedContext.constraints.length})</div>
                    {resolvedContext.constraints.map((c, i) => (
                      <div key={i} className="text-[10px] font-mono text-red-400">
                        ! {String(c.summary || c.source_doc || JSON.stringify(c))}
                      </div>
                    ))}
                  </div>
                )}

                {resolvedContext.knowledge && resolvedContext.knowledge.length > 0 && (
                  <div className="bg-surface-secondary rounded p-3 space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Knowledge ({resolvedContext.knowledge.length})</div>
                    {resolvedContext.knowledge.map((k, i) => (
                      <div key={i} className="text-[10px] font-mono text-text-secondary">
                        <Brain size={8} className="inline mr-1 text-purple-400" />
                        {String(k.summary || k.knowledge_type || JSON.stringify(k))}
                        {k.knowledge_type && <span className="text-text-tertiary ml-1">({String(k.knowledge_type)})</span>}
                      </div>
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

        {/* Artifacts Tab */}
        {tab === 'artifacts' && (
          <div className="space-y-3">
            <div className="text-[9px] font-mono text-text-tertiary uppercase flex items-center gap-1">
              <Archive size={10} /> Artifact Registry
            </div>
            {artifacts.length === 0 && (
              <div className="text-[10px] font-mono text-text-tertiary text-center py-8">No artifacts indexed</div>
            )}
            {artifacts.map((a) => (
              <div key={a.artifact_id} className="bg-surface-secondary rounded p-3 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono text-text-primary">{a.name}</span>
                  <span className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded ${
                    a.status === 'active' ? 'bg-green-400/10 text-green-400' : 'bg-surface-secondary text-text-tertiary'
                  }`}>{a.status}</span>
                </div>
                <div className="text-[9px] font-mono text-text-tertiary">{a.artifact_type} · {a.source_path}</div>
                {a.entity_refs.length > 0 && (
                  <div className="text-[9px] font-mono text-cyan">refs: {a.entity_refs.join(', ')}</div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Files Tab */}
        {tab === 'files' && (
          <div className="space-y-3">
            <div className="text-[9px] font-mono text-text-tertiary uppercase flex items-center gap-1">
              <FileText size={10} /> Repository Awareness
            </div>
            {repoSnapshot ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-surface-secondary rounded p-3">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Files</div>
                    <div className="text-2xl font-mono text-cyan">{repoSnapshot.file_count}</div>
                  </div>
                  <div className="bg-surface-secondary rounded p-3">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Branch</div>
                    <div className="text-[11px] font-mono text-text-primary mt-1">{repoSnapshot.branch || 'N/A'}</div>
                  </div>
                </div>
                {repoSnapshot.files_by_category && Object.keys(repoSnapshot.files_by_category).length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">By Category</div>
                    {Object.entries(repoSnapshot.files_by_category).sort(([, a], [, b]) => b - a).map(([cat, count]) => (
                      <div key={cat} className="flex items-center justify-between bg-surface-secondary rounded px-3 py-2">
                        <span className="text-[10px] font-mono text-text-secondary">{cat}</span>
                        <span className="text-[11px] font-mono text-text-primary">{count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-[10px] font-mono text-text-tertiary text-center py-8">No repository snapshot</div>
            )}
          </div>
        )}

        {/* Docs Tab */}
        {tab === 'docs' && (
          <div className="space-y-3">
            <div className="text-[9px] font-mono text-text-tertiary uppercase flex items-center gap-1">
              <BookOpen size={10} /> Documentation Awareness
            </div>
            {docsSnapshot ? (
              <div className="space-y-3">
                <div className="bg-surface-secondary rounded p-3">
                  <div className="text-[9px] font-mono text-text-tertiary uppercase">Total Documents</div>
                  <div className="text-2xl font-mono text-cyan">{docsSnapshot.total_docs}</div>
                </div>
                {docsSnapshot.by_status && Object.keys(docsSnapshot.by_status).length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">By Status</div>
                    {Object.entries(docsSnapshot.by_status).map(([status, count]) => (
                      <div key={status} className="flex items-center justify-between bg-surface-secondary rounded px-3 py-2">
                        <span className="text-[10px] font-mono text-text-secondary">{status}</span>
                        <span className="text-[11px] font-mono text-text-primary">{count}</span>
                      </div>
                    ))}
                  </div>
                )}
                {docsSnapshot.stale_docs && docsSnapshot.stale_docs.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[9px] font-mono text-yellow-400 uppercase">Stale ({docsSnapshot.stale_docs.length})</div>
                    {docsSnapshot.stale_docs.map((d, i) => (
                      <div key={i} className="text-[10px] font-mono text-text-secondary bg-surface-secondary rounded px-3 py-2">
                        {String((d as Record<string, unknown>).name || JSON.stringify(d))}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-[10px] font-mono text-text-tertiary text-center py-8">No documentation snapshot</div>
            )}
          </div>
        )}

        {/* Runtime Tab */}
        {tab === 'runtime' && (
          <div className="space-y-3">
            <div className="text-[9px] font-mono text-text-tertiary uppercase flex items-center gap-1">
              <Activity size={10} /> Runtime Awareness
            </div>
            {runtimeSnapshot ? (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-surface-secondary rounded p-3">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Processes</div>
                    <div className="text-xl font-mono text-cyan">{runtimeSnapshot.processes?.length ?? 0}</div>
                  </div>
                  <div className="bg-surface-secondary rounded p-3">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Containers</div>
                    <div className="text-xl font-mono text-cyan">{runtimeSnapshot.containers?.length ?? 0}</div>
                  </div>
                  <div className="bg-surface-secondary rounded p-3">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Active Work</div>
                    <div className="text-xl font-mono text-yellow-400">{runtimeSnapshot.active_work_packets?.length ?? 0}</div>
                  </div>
                </div>

                {runtimeSnapshot.blocked_work && runtimeSnapshot.blocked_work.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[9px] font-mono text-red-400 uppercase">Blocked ({runtimeSnapshot.blocked_work.length})</div>
                    {runtimeSnapshot.blocked_work.map((b, i) => (
                      <div key={i} className="text-[10px] font-mono text-text-secondary bg-surface-secondary rounded px-3 py-2">
                        {String((b as Record<string, unknown>).node_id || JSON.stringify(b))}
                        {(b as Record<string, unknown>).blocker && (
                          <span className="text-red-400 ml-1">← {String((b as Record<string, unknown>).blocker)}</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {runtimeSnapshot.containers && runtimeSnapshot.containers.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Containers</div>
                    {runtimeSnapshot.containers.map((c, i) => (
                      <div key={i} className="flex items-center justify-between bg-surface-secondary rounded px-3 py-2">
                        <span className="text-[10px] font-mono text-text-secondary">{String((c as Record<string, unknown>).name || 'unknown')}</span>
                        <span className={`text-[9px] font-mono ${
                          String((c as Record<string, unknown>).status) === 'running' ? 'text-green-400' : 'text-red-400'
                        }`}>{String((c as Record<string, unknown>).status || 'unknown')}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-[10px] font-mono text-text-tertiary text-center py-8">No runtime snapshot</div>
            )}
          </div>
        )}

        {/* Knowledge Tab */}
        {tab === 'knowledge' && (
          <div className="space-y-3">
            <div className="text-[9px] font-mono text-text-tertiary uppercase flex items-center gap-1">
              <Brain size={10} /> Knowledge Awareness
            </div>
            {knowledgeSnapshot ? (
              <div className="space-y-3">
                <div className="bg-surface-secondary rounded p-3">
                  <div className="text-[9px] font-mono text-text-tertiary uppercase">Total Knowledge Entries</div>
                  <div className="text-2xl font-mono text-cyan">{knowledgeSnapshot.total}</div>
                </div>

                {knowledgeSnapshot.by_type && Object.keys(knowledgeSnapshot.by_type).length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">By Type</div>
                    {Object.entries(knowledgeSnapshot.by_type).sort(([, a], [, b]) => b - a).map(([type, count]) => (
                      <div key={type} className="flex items-center justify-between bg-surface-secondary rounded px-3 py-2">
                        <span className="text-[10px] font-mono text-text-secondary">{type.replace('_', ' ')}</span>
                        <span className="text-[11px] font-mono text-text-primary">{count}</span>
                      </div>
                    ))}
                  </div>
                )}

                {knowledgeSnapshot.recent && knowledgeSnapshot.recent.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[9px] font-mono text-text-tertiary uppercase">Recent Entries</div>
                    {knowledgeSnapshot.recent.slice(0, 10).map((k, i) => (
                      <div key={i} className="bg-surface-secondary rounded px-3 py-2 space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className={`text-[9px] font-mono uppercase px-1 py-0.5 rounded ${
                            String((k as Record<string, unknown>).knowledge_type) === 'decision' ? 'bg-green-400/10 text-green-400'
                            : String((k as Record<string, unknown>).knowledge_type) === 'constraint' ? 'bg-red-400/10 text-red-400'
                            : 'bg-surface-secondary text-text-tertiary'
                          }`}>{String((k as Record<string, unknown>).knowledge_type || 'unknown')}</span>
                        </div>
                        <div className="text-[10px] font-mono text-text-secondary">
                          {String((k as Record<string, unknown>).summary || JSON.stringify(k))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-[10px] font-mono text-text-tertiary text-center py-8">No knowledge snapshot</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
