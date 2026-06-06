import { useState } from 'react'
import { useWorldModelStore } from '../stores/worldModelStore'
import { usePolling } from '../hooks/usePolling'

const CONFIDENCE_COLORS = (v: number) =>
  v >= 0.8 ? 'text-ok' : v >= 0.5 ? 'text-cyan' : v >= 0.3 ? 'text-warn' : 'text-danger'

const RISK_BADGE: Record<string, string> = {
  low: 'bg-ok/20 text-ok',
  medium: 'bg-warn/20 text-warn',
  high: 'bg-danger/20 text-danger',
  critical: 'bg-danger/30 text-danger',
}

const TABS = [
  { id: 'world' as const, label: 'World' },
  { id: 'graph' as const, label: 'Dependencies' },
  { id: 'contradictions' as const, label: 'Search' },
  { id: 'compose' as const, label: 'Simulate' },
  { id: 'outcomes' as const, label: 'Observations' },
  { id: 'memory' as const, label: 'Instance' },
]

function TabBar() {
  const tab = useWorldModelStore((s) => s.tab)
  const setTab = useWorldModelStore((s) => s.setTab)
  const status = useWorldModelStore((s) => s.status)

  return (
    <div className="flex items-center gap-1 px-4 py-2 border-b border-border bg-canvas">
      {TABS.map((t) => (
        <button
          key={t.id}
          onClick={() => setTab(t.id)}
          className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
            tab === t.id
              ? 'bg-cyan/20 text-cyan'
              : 'text-text-secondary hover:text-text-primary hover:bg-surface-overlay'
          }`}
        >
          {t.label}
          {t.id === 'world' && status && (
            <span className="ml-1.5 text-text-tertiary">{status.canonical.pattern_count}</span>
          )}
          {t.id === 'outcomes' && status && (
            <span className="ml-1.5 text-text-tertiary">{status.instance.observation_count}</span>
          )}
        </button>
      ))}
    </div>
  )
}

function WorldTab() {
  const status = useWorldModelStore((s) => s.status)
  const patterns = useWorldModelStore((s) => s.patterns)
  const canonicalDomains = useWorldModelStore((s) => s.canonicalDomains)
  const loading = useWorldModelStore((s) => s.loading)
  const fetchPatternDetail = useWorldModelStore((s) => s.fetchPatternDetail)
  const selectedPattern = useWorldModelStore((s) => s.selectedPattern)

  if (loading) return <Empty msg="Loading reality model..." />
  if (!status) return <Empty msg="Reality model not yet available" />

  const byDomain: Record<string, typeof patterns> = {}
  for (const p of patterns) {
    if (!byDomain[p.domain]) byDomain[p.domain] = []
    byDomain[p.domain].push(p)
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Patterns" value={status.canonical.pattern_count} />
        <Stat label="Relationships" value={status.canonical.relationship_count} />
        <Stat label="Domains" value={status.canonical.domains.length} />
        <Stat
          label="Avg Confidence"
          value={`${((status.canonical?.avg_confidence ?? 0) * 100).toFixed(0)}%`}
          color={(status.canonical?.avg_confidence ?? 0) >= 0.5 ? 'ok' : 'warn'}
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <h3 className="wv-label mb-2">Layers</h3>
          <div className="flex gap-1">
            {status.layers.map((l) => (
              <span key={l} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan/10 text-cyan">{l}</span>
            ))}
          </div>
        </div>
        <div>
          <h3 className="wv-label mb-2">Domains</h3>
          <div className="flex flex-wrap gap-1">
            {canonicalDomains.map((d) => (
              <span key={d.domain} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-overlay text-text-secondary">
                {d.domain} <span className="text-text-tertiary">({d.pattern_count})</span>
              </span>
            ))}
            {canonicalDomains.length === 0 && (
              <span className="text-[10px] text-text-tertiary">No domains yet</span>
            )}
          </div>
        </div>
      </div>

      {Object.entries(byDomain).sort().map(([domain, domainPatterns]) => (
        <section key={domain}>
          <h3 className="wv-label mb-2">{domain} ({domainPatterns.length})</h3>
          <div className="space-y-1">
            {domainPatterns
              .sort((a, b) => b.effective_confidence - a.effective_confidence)
              .map((p) => (
                <div
                  key={p.id}
                  onClick={() => fetchPatternDetail(p.name)}
                  className="flex items-center gap-2 py-1 px-2 rounded hover:bg-surface-overlay cursor-pointer"
                >
                  <span className={`text-[10px] font-mono w-10 text-right ${CONFIDENCE_COLORS(p.effective_confidence ?? 0)}`}>
                    {((p.effective_confidence ?? 0) * 100).toFixed(0)}%
                  </span>
                  <span className="text-xs text-text-primary flex-1 truncate">{p.name}</span>
                  <span className="text-[10px] text-text-tertiary">{p.evidence_count} ev</span>
                  {p.tags.length > 0 && (
                    <span className="text-[10px] text-text-tertiary">{p.tags[0]}</span>
                  )}
                </div>
              ))}
          </div>
        </section>
      ))}

      {patterns.length === 0 && (
        <div className="text-center py-6">
          <p className="text-xs text-text-tertiary font-mono">No canonical patterns yet</p>
          <p className="text-[10px] text-text-tertiary mt-1">Patterns are promoted from instance observations through governed review.</p>
        </div>
      )}

      {selectedPattern && (
        <section className="wv-card p-3 border border-cyan/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-cyan">{selectedPattern.name}</span>
            <span className={`text-[10px] font-mono ${CONFIDENCE_COLORS(selectedPattern.effective_confidence ?? 0)}`}>
              {((selectedPattern.effective_confidence ?? 0) * 100).toFixed(0)}% confidence
            </span>
          </div>
          <p className="text-xs text-text-secondary mb-2">{selectedPattern.description}</p>
          <div className="flex items-center gap-3 text-[10px] text-text-tertiary mb-2">
            <span>domain: {selectedPattern.domain}</span>
            <span>{selectedPattern.evidence_count} evidence</span>
            <span>promoted: {new Date(selectedPattern.promoted_at).toLocaleDateString()}</span>
            <span>confirmed: {new Date(selectedPattern.last_confirmed).toLocaleDateString()}</span>
          </div>
          {selectedPattern.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {selectedPattern.tags.map((t) => (
                <span key={t} className="text-[10px] font-mono px-1 py-0.5 rounded bg-surface-overlay text-text-tertiary">{t}</span>
              ))}
            </div>
          )}
          {selectedPattern.relationships.length > 0 && (
            <div>
              <span className="text-[10px] text-text-tertiary">Relationships:</span>
              <div className="space-y-0.5 mt-1">
                {selectedPattern.relationships.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 text-[10px] font-mono">
                    <span className="text-text-primary">{r.name}</span>
                    <span className="text-text-tertiary">{r.type}</span>
                    <span className="text-cyan">{((r.strength ?? 0) * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  )
}

function GraphTab() {
  const patterns = useWorldModelStore((s) => s.patterns)
  const relationships = useWorldModelStore((s) => s.relationships)
  const fetchRelationships = useWorldModelStore((s) => s.fetchRelationships)
  const loading = useWorldModelStore((s) => s.loading)
  const status = useWorldModelStore((s) => s.status)
  const [selectedName, setSelectedName] = useState<string | null>(null)

  if (loading) return <Empty msg="Loading dependency graph..." />
  if (!status) return <Empty msg="Reality model not loaded" />

  const handleSelect = (name: string) => {
    setSelectedName(name)
    fetchRelationships(name)
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <Stat label="Patterns" value={status.canonical.pattern_count} />
        <Stat label="Relationships" value={status.canonical.relationship_count} />
        <Stat label="Avg Evidence" value={(status.canonical?.avg_evidence_count ?? 0).toFixed(1)} />
      </div>

      <section>
        <h3 className="wv-label mb-2">Select pattern to view relationships</h3>
        <div className="max-h-40 overflow-y-auto space-y-0.5">
          {patterns.map((p) => (
            <div
              key={p.id}
              onClick={() => handleSelect(p.name)}
              className={`flex items-center gap-2 py-0.5 px-2 rounded cursor-pointer text-[11px] font-mono ${
                selectedName === p.name
                  ? 'bg-cyan/20 text-cyan'
                  : 'text-text-primary hover:bg-surface-overlay'
              }`}
            >
              <span className="flex-1 truncate">{p.name}</span>
              <span className="text-text-tertiary">{p.domain}</span>
            </div>
          ))}
          {patterns.length === 0 && (
            <p className="text-xs text-text-tertiary">No patterns available</p>
          )}
        </div>
      </section>

      {selectedName && (
        <section>
          <h3 className="wv-label mb-2">Relationships: {selectedName}</h3>
          {relationships.length > 0 ? (
            <div className="space-y-1">
              {relationships.map((r, i) => (
                <div key={i} className="flex items-center gap-2 py-0.5 text-[11px] font-mono">
                  <span className="text-text-primary">{selectedName}</span>
                  <span className="text-text-tertiary">&rarr;</span>
                  <span className="text-text-primary">{r.name}</span>
                  <span className="text-text-tertiary ml-auto">{r.type}</span>
                  <span className={`text-[9px] ${(r.strength ?? 0) >= 0.7 ? 'text-cyan' : 'text-text-tertiary'}`}>
                    {((r.strength ?? 0) * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-text-tertiary">No relationships for this pattern</p>
          )}
        </section>
      )}
    </div>
  )
}

function SearchTab() {
  const searchCanonical = useWorldModelStore((s) => s.searchCanonical)
  const searchResults = useWorldModelStore((s) => s.searchResults)
  const simulate = useWorldModelStore((s) => s.simulate)
  const composing = useWorldModelStore((s) => s.composing)
  const [query, setQuery] = useState('')

  const handleSearch = () => {
    if (query.trim()) searchCanonical(query.trim())
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSearch() }}
          placeholder="Search canonical patterns..."
          className="flex-1 px-3 py-1.5 text-xs font-mono bg-surface border border-border rounded text-text-primary placeholder-text-tertiary focus:border-cyan focus:outline-none"
        />
        <button
          onClick={handleSearch}
          disabled={!query.trim()}
          className="px-3 py-1.5 text-xs font-mono bg-cyan/20 text-cyan rounded hover:bg-cyan/30 disabled:opacity-50"
        >
          SEARCH
        </button>
      </div>

      {searchResults.length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Results ({searchResults.length})</h3>
          <div className="space-y-1.5">
            {searchResults.map((r) => (
              <div key={r.id} className="wv-card p-2">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-mono ${CONFIDENCE_COLORS(r.effective_confidence ?? 0)}`}>
                    {((r.effective_confidence ?? 0) * 100).toFixed(0)}%
                  </span>
                  <span className="text-xs text-text-primary flex-1">{r.name || r.content}</span>
                  <span className="text-[10px] text-text-tertiary">{r.domain}</span>
                </div>
                {r.description && (
                  <p className="text-[10px] text-text-secondary mt-1 ml-10">{r.description}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {searchResults.length > 0 && (
        <div className="flex items-center gap-2">
          <button
            onClick={() => simulate(`Analyze patterns related to: ${query}`)}
            disabled={composing}
            className="px-3 py-1.5 text-xs font-mono bg-warn/20 text-warn rounded hover:bg-warn/30 disabled:opacity-50"
          >
            {composing ? 'SIMULATING...' : 'SIMULATE'}
          </button>
          <span className="text-[10px] text-text-tertiary">Run hypothesis test against reality model</span>
        </div>
      )}

      {searchResults.length === 0 && query && (
        <p className="text-xs text-text-tertiary text-center py-4">No patterns match &ldquo;{query}&rdquo;</p>
      )}
    </div>
  )
}

function SimulateTab() {
  const simulation = useWorldModelStore((s) => s.simulation)
  const simulate = useWorldModelStore((s) => s.simulate)
  const composing = useWorldModelStore((s) => s.composing)
  const [hypothesis, setHypothesis] = useState('')

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={hypothesis}
          onChange={(e) => setHypothesis(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && hypothesis.trim()) simulate(hypothesis.trim()) }}
          placeholder="Enter hypothesis to simulate..."
          className="flex-1 px-3 py-1.5 text-xs font-mono bg-surface border border-border rounded text-text-primary placeholder-text-tertiary focus:border-cyan focus:outline-none"
        />
        <button
          onClick={() => hypothesis.trim() && simulate(hypothesis.trim())}
          disabled={composing || !hypothesis.trim()}
          className="px-3 py-1.5 text-xs font-mono bg-cyan/20 text-cyan rounded hover:bg-cyan/30 disabled:opacity-50"
        >
          {composing ? 'SIMULATING...' : 'SIMULATE'}
        </button>
      </div>

      {simulation && (
        <div className="space-y-3">
          <div className="wv-card p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-text-primary">{simulation.hypothesis}</span>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                  simulation.safe_to_execute ? 'bg-ok/20 text-ok' : 'bg-danger/20 text-danger'
                }`}>
                  {simulation.safe_to_execute ? 'SAFE' : 'RISKY'}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-4 gap-2 text-[10px] text-text-tertiary">
              <span>{simulation.step_count} steps</span>
              <span>{((simulation.overall_confidence ?? 0) * 100).toFixed(0)}% confidence</span>
              <span>{(simulation.duration_ms ?? 0).toFixed(0)}ms</span>
              <span>{simulation.predicted_outcome}</span>
            </div>
          </div>

          {simulation.risk_factors.length > 0 && (
            <section>
              <h3 className="wv-label mb-2 text-danger">Risk Factors</h3>
              <div className="space-y-1">
                {simulation.risk_factors.map((rf, i) => (
                  <div key={i} className="flex items-center gap-2 py-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-danger" />
                    <span className="text-xs text-danger/80">{rf}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {simulation.matched_patterns.length > 0 && (
            <section>
              <h3 className="wv-label mb-2">Matched Patterns</h3>
              <div className="flex flex-wrap gap-1">
                {simulation.matched_patterns.map((p) => (
                  <span key={p} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan/10 text-cyan">{p}</span>
                ))}
              </div>
            </section>
          )}

          {simulation.ai_risk_analysis && Object.keys(simulation.ai_risk_analysis).length > 0 && (
            <section>
              <h3 className="wv-label mb-2">AI Risk Analysis</h3>
              <div className="wv-card p-2">
                {simulation.ai_risk_analysis.severity && (
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                      RISK_BADGE[simulation.ai_risk_analysis.severity as string] || 'bg-surface-overlay text-text-tertiary'
                    }`}>
                      {simulation.ai_risk_analysis.severity as string}
                    </span>
                    {simulation.ai_risk_analysis.confidence != null && (
                      <span className="text-[10px] text-text-tertiary">
                        {(((simulation.ai_risk_analysis.confidence as number) ?? 0) * 100).toFixed(0)}% conf
                      </span>
                    )}
                  </div>
                )}
                {simulation.ai_risk_analysis.reasoning && (
                  <p className="text-xs text-text-secondary">{simulation.ai_risk_analysis.reasoning as string}</p>
                )}
                {Array.isArray(simulation.ai_risk_analysis.mitigations) && (
                  <div className="mt-1 space-y-0.5">
                    {(simulation.ai_risk_analysis.mitigations as string[]).map((m, i) => (
                      <p key={i} className="text-[10px] text-text-tertiary">• {m}</p>
                    ))}
                  </div>
                )}
              </div>
            </section>
          )}
        </div>
      )}

      {!simulation && !composing && (
        <div className="text-center py-8">
          <p className="text-xs text-text-tertiary">Test hypotheses against the reality model.</p>
          <p className="text-[10px] text-text-tertiary mt-1">Hypothesis → Pattern matching → Risk analysis → Predicted outcome</p>
        </div>
      )}
    </div>
  )
}

function ObservationsTab() {
  const recentObservations = useWorldModelStore((s) => s.recentObservations)
  const instanceDomains = useWorldModelStore((s) => s.instanceDomains)
  const loading = useWorldModelStore((s) => s.loading)
  const status = useWorldModelStore((s) => s.status)

  if (loading) return <Empty msg="Loading observations..." />
  if (!status) return <Empty msg="Instance model not yet available" />

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Observations" value={status.instance.observation_count} />
        <Stat label="Domains" value={status.instance.domains.length} />
        <Stat
          label="Avg Confidence"
          value={`${(status.instance.avg_effective_confidence * 100).toFixed(0)}%`}
          color={status.instance.avg_effective_confidence >= 0.3 ? 'ok' : 'warn'}
        />
        <Stat
          label="Newest"
          value={status.instance.newest ? new Date(status.instance.newest).toLocaleTimeString() : '—'}
        />
      </div>

      {instanceDomains.length > 0 && (
        <section>
          <h3 className="wv-label mb-2">Instance Domains</h3>
          <div className="flex flex-wrap gap-1">
            {instanceDomains.map((d) => (
              <span key={d.domain} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-overlay text-text-secondary">
                {d.domain} <span className="text-text-tertiary">({d.observation_count})</span>
              </span>
            ))}
          </div>
        </section>
      )}

      <section>
        <h3 className="wv-label mb-2">Recent Observations</h3>
        {recentObservations.length > 0 ? (
          <div className="space-y-1">
            {recentObservations.map((o) => (
              <div key={o.id} className="wv-card p-2">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`text-[10px] font-mono ${CONFIDENCE_COLORS(o.effective_confidence)}`}>
                    {(o.effective_confidence * 100).toFixed(0)}%
                  </span>
                  <span className="text-[10px] font-mono text-text-tertiary">{o.domain}</span>
                  <span className="text-[10px] text-text-tertiary ml-auto">
                    {new Date(o.observed_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-text-primary">{o.content}</p>
                {o.tags.length > 0 && (
                  <div className="flex gap-1 mt-1">
                    {o.tags.map((t) => (
                      <span key={t} className="text-[9px] font-mono px-1 rounded bg-surface-overlay text-text-tertiary">{t}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-tertiary text-center py-4">No observations recorded yet</p>
        )}
      </section>
    </div>
  )
}

function InstanceTab() {
  const instanceStats = useWorldModelStore((s) => s.instanceStats)
  const status = useWorldModelStore((s) => s.status)
  const loading = useWorldModelStore((s) => s.loading)

  if (loading) return <Empty msg="Loading instance stats..." />
  if (!status || !instanceStats) return <Empty msg="Instance stats not yet available" />

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Observations" value={instanceStats.observation_count} />
        <Stat label="Domains" value={instanceStats.domains.length} />
        <Stat
          label="Avg Confidence"
          value={`${(instanceStats.avg_effective_confidence * 100).toFixed(0)}%`}
          color={instanceStats.avg_effective_confidence >= 0.3 ? 'ok' : 'warn'}
        />
        <Stat label="Canonical" value={status.canonical.pattern_count} color="cyan" />
      </div>

      <section>
        <h3 className="wv-label mb-2">Temporal Range</h3>
        <div className="wv-card p-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-[10px] text-text-tertiary block">Oldest observation</span>
              <span className="text-xs font-mono text-text-primary">
                {instanceStats.oldest ? new Date(instanceStats.oldest).toLocaleString() : '—'}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-text-tertiary block">Newest observation</span>
              <span className="text-xs font-mono text-text-primary">
                {instanceStats.newest ? new Date(instanceStats.newest).toLocaleString() : '—'}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section>
        <h3 className="wv-label mb-2">Instance Domains</h3>
        <div className="space-y-1">
          {instanceStats.domains.map((d) => (
            <div key={d} className="flex items-center gap-2 py-0.5">
              <span className="text-xs text-text-primary">{d}</span>
            </div>
          ))}
          {instanceStats.domains.length === 0 && (
            <p className="text-xs text-text-tertiary">No domains recorded</p>
          )}
        </div>
      </section>

      <section>
        <h3 className="wv-label mb-2">Reality Model Layers</h3>
        <div className="space-y-2">
          <div className="wv-card p-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-cyan font-mono">canonical</span>
              <span className="text-[10px] text-text-tertiary">
                {status.canonical.pattern_count} patterns, {status.canonical.relationship_count} relationships
              </span>
            </div>
            <p className="text-[10px] text-text-tertiary mt-0.5">
              Sacred, governance-protected. {(status.canonical.avg_confidence * 100).toFixed(0)}% avg confidence.
            </p>
          </div>
          <div className="wv-card p-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-warn font-mono">instance</span>
              <span className="text-[10px] text-text-tertiary">
                {instanceStats.observation_count} observations
              </span>
            </div>
            <p className="text-[10px] text-text-tertiary mt-0.5">
              Ephemeral, high-volume. 14-day half-life decay. {(instanceStats.avg_effective_confidence * 100).toFixed(0)}% avg confidence.
            </p>
          </div>
          <div className="wv-card p-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-secondary font-mono">simulation</span>
              <span className="text-[10px] text-text-tertiary">non-mutating hypothesis testing</span>
            </div>
            <p className="text-[10px] text-text-tertiary mt-0.5">
              Clones instance reality for dry-run predictions. Use the Simulate tab.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}

export function WorldModelPanel() {
  const tab = useWorldModelStore((s) => s.tab)
  const fetchAll = useWorldModelStore((s) => s.fetchAll)

  usePolling(fetchAll, 20000)

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TabBar />
      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'world' && <WorldTab />}
        {tab === 'graph' && <GraphTab />}
        {tab === 'contradictions' && <SearchTab />}
        {tab === 'compose' && <SimulateTab />}
        {tab === 'outcomes' && <ObservationsTab />}
        {tab === 'memory' && <InstanceTab />}
      </div>
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: string | number; color?: string }) {
  const colorClass = color === 'ok' ? 'text-ok' : color === 'warn' ? 'text-warn' : color === 'danger' ? 'text-danger' : color === 'cyan' ? 'text-cyan' : 'text-text-primary'
  return (
    <div className="wv-card px-2 py-1.5 text-center">
      <div className="text-[8px] text-text-tertiary uppercase">{label}</div>
      <div className={`text-xs font-mono font-semibold ${colorClass}`}>{value}</div>
    </div>
  )
}

function Empty({ msg }: { msg: string }) {
  return (
    <div className="h-full flex items-center justify-center">
      <p className="text-text-tertiary text-sm">{msg}</p>
    </div>
  )
}
