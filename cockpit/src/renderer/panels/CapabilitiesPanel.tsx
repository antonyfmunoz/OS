import { useEffect, useState } from 'react'
import {
  Layers,
  BarChart3,
  AlertTriangle,
  Network,
  TrendingUp,
  RefreshCw,
} from 'lucide-react'
import { useCapabilityIntelligenceStore } from '../stores/capabilityIntelligenceStore'

type Tab = 'portfolio' | 'gaps' | 'graph' | 'compounding'

const TABS: { id: Tab; label: string; icon: typeof Layers }[] = [
  { id: 'portfolio', label: 'Portfolio', icon: BarChart3 },
  { id: 'gaps', label: 'Gaps', icon: AlertTriangle },
  { id: 'graph', label: 'Graph', icon: Network },
  { id: 'compounding', label: 'Compounding', icon: TrendingUp },
]

function Badge({ label, variant = 'default' }: { label: string; variant?: string }) {
  const colors: Record<string, string> = {
    thriving: 'bg-emerald-500/20 text-emerald-400',
    healthy: 'bg-blue-500/20 text-blue-400',
    stagnating: 'bg-amber-500/20 text-amber-400',
    decaying: 'bg-red-500/20 text-red-400',
    institutional: 'bg-emerald-500/20 text-emerald-400',
    operational: 'bg-blue-500/20 text-blue-400',
    validated: 'bg-cyan-500/20 text-cyan-400',
    emerging: 'bg-amber-500/20 text-amber-400',
    critical: 'bg-red-500/20 text-red-400',
    high: 'bg-orange-500/20 text-orange-400',
    medium: 'bg-amber-500/20 text-amber-400',
    low: 'bg-emerald-500/20 text-emerald-400',
    depends_on: 'bg-blue-500/20 text-blue-400',
    composes: 'bg-cyan-500/20 text-cyan-400',
    enables: 'bg-emerald-500/20 text-emerald-400',
    conflicts_with: 'bg-red-500/20 text-red-400',
    default: 'bg-zinc-500/20 text-zinc-400',
  }
  const cls = colors[variant] || colors[label] || colors.default
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 mb-3">
      <h3 className="text-sm font-semibold text-secondary mb-2">{title}</h3>
      {children}
    </div>
  )
}

function PortfolioTab() {
  const { portfolio, loading, fetchPortfolio } = useCapabilityIntelligenceStore()

  useEffect(() => { fetchPortfolio() }, [fetchPortfolio])

  if (loading) return <div className="text-muted text-sm p-4">Loading portfolio...</div>
  if (!portfolio) return <div className="text-muted text-sm p-4">No portfolio data available</div>

  const health = String(portfolio.health ?? 'unknown')
  const total = Number(portfolio.total_capabilities ?? 0)
  const score = Number(portfolio.compounding_score ?? 0)
  const velocity = Number(portfolio.maturity_velocity ?? 0)
  const byMaturity = (portfolio.by_maturity ?? {}) as Record<string, number>
  const topCaps = (portfolio.top_capabilities ?? []) as Record<string, unknown>[]
  const weakest = (portfolio.weakest_capabilities ?? []) as Record<string, unknown>[]
  const gaps = (portfolio.critical_gaps ?? []) as Record<string, unknown>[]

  return (
    <div className="space-y-3">
      <SectionCard title="Health Overview">
        <div className="flex items-center gap-3 mb-3">
          <Badge label={health} variant={health} />
          <span className="text-sm text-muted">{total} capabilities</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="text-center">
            <div className="text-2xl font-bold text-primary">{score.toFixed(2)}</div>
            <div className="text-xs text-muted">Compounding Score</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-primary">{(velocity * 100).toFixed(0)}%</div>
            <div className="text-xs text-muted">Maturity Velocity</div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Maturity Distribution">
        {Object.entries(byMaturity).length === 0 ? (
          <p className="text-muted text-sm">No capabilities registered</p>
        ) : (
          <div className="space-y-1">
            {Object.entries(byMaturity).map(([mat, count]) => (
              <div key={mat} className="flex items-center justify-between">
                <Badge label={mat} variant={mat} />
                <span className="text-sm font-mono text-primary">{count}</span>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      {topCaps.length > 0 && (
        <SectionCard title="Top Capabilities">
          {topCaps.map((c, i) => (
            <div key={i} className="flex items-center justify-between py-1">
              <span className="text-sm text-primary">{String(c.name ?? '')}</span>
              <Badge label={String(c.maturity ?? '')} variant={String(c.maturity ?? '')} />
            </div>
          ))}
        </SectionCard>
      )}

      {weakest.length > 0 && (
        <SectionCard title="Weakest Capabilities">
          {weakest.map((c, i) => (
            <div key={i} className="flex items-center justify-between py-1">
              <span className="text-sm text-primary">{String(c.name ?? '')}</span>
              <Badge label={String(c.maturity ?? '')} variant={String(c.maturity ?? '')} />
            </div>
          ))}
        </SectionCard>
      )}

      {gaps.length > 0 && (
        <SectionCard title="Critical Gaps">
          {gaps.map((g, i) => (
            <div key={i} className="py-1">
              <span className="text-sm text-primary">{String(g.recommendation ?? g.required_capability ?? '')}</span>
            </div>
          ))}
        </SectionCard>
      )}
    </div>
  )
}

function GapsTab() {
  const { gaps, criticalGaps, fetchGaps, fetchCriticalGaps } = useCapabilityIntelligenceStore()
  const [showCriticalOnly, setShowCriticalOnly] = useState(false)

  useEffect(() => { fetchGaps(); fetchCriticalGaps() }, [fetchGaps, fetchCriticalGaps])

  const displayed = showCriticalOnly ? criticalGaps : gaps

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <button
          onClick={() => setShowCriticalOnly(!showCriticalOnly)}
          className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
            showCriticalOnly
              ? 'bg-red-500/20 text-red-400'
              : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
          }`}
        >
          {showCriticalOnly ? 'Critical Only' : 'All Gaps'}
        </button>
        <span className="text-xs text-muted">{displayed.length} gap(s)</span>
      </div>

      {displayed.length === 0 ? (
        <p className="text-muted text-sm p-4">No capability gaps detected</p>
      ) : (
        displayed.map((g, i) => (
          <SectionCard key={i} title={String(g.required_capability ?? 'Unknown')}>
            <div className="flex items-center gap-2 mb-1">
              <Badge label={String(g.severity ?? 'unknown')} variant={String(g.severity ?? '')} />
              {g.goal_title && <span className="text-xs text-muted">Goal: {String(g.goal_title)}</span>}
            </div>
            {g.matched_capability_name && (
              <p className="text-xs text-muted">
                Matched: {String(g.matched_capability_name)} ({String(g.matched_maturity ?? '')})
              </p>
            )}
            {g.recommendation && (
              <p className="text-xs text-cyan-400 mt-1">{String(g.recommendation)}</p>
            )}
          </SectionCard>
        ))
      )}
    </div>
  )
}

function GraphTab() {
  const { graph, bottlenecks, fetchGraph, fetchBottlenecks } = useCapabilityIntelligenceStore()

  useEffect(() => { fetchGraph(); fetchBottlenecks() }, [fetchGraph, fetchBottlenecks])

  const { edges, summary } = graph

  return (
    <div className="space-y-3">
      <SectionCard title="Graph Summary">
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <div className="text-lg font-bold text-primary">{Number(summary.total_edges ?? 0)}</div>
            <div className="text-xs text-muted">Edges</div>
          </div>
          <div>
            <div className="text-lg font-bold text-primary">{Number(summary.total_nodes ?? 0)}</div>
            <div className="text-xs text-muted">Nodes</div>
          </div>
          <div>
            <div className="text-lg font-bold text-primary">{Number(summary.cycles ?? 0)}</div>
            <div className="text-xs text-muted">Cycles</div>
          </div>
        </div>
      </SectionCard>

      {edges.length > 0 && (
        <SectionCard title="Dependency Edges">
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {edges.map((e, i) => (
              <div key={i} className="flex items-center gap-2 text-xs py-1 border-b border-border/50 last:border-0">
                <span className="text-primary font-mono">{String(e.source_id ?? '').slice(0, 12)}</span>
                <Badge label={String(e.relation ?? '')} variant={String(e.relation ?? '')} />
                <span className="text-primary font-mono">{String(e.target_id ?? '').slice(0, 12)}</span>
                <span className="text-muted ml-auto">{Number(e.strength ?? 0).toFixed(1)}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {bottlenecks.length > 0 && (
        <SectionCard title="Bottlenecks">
          {bottlenecks.map((b, i) => (
            <div key={i} className="flex items-center justify-between py-1">
              <span className="text-sm text-primary">{String((b as Record<string, unknown>).capability_id ?? '')}</span>
              <span className="text-xs text-amber-400">{Number((b as Record<string, unknown>).dependent_count ?? 0)} dependents</span>
            </div>
          ))}
        </SectionCard>
      )}
    </div>
  )
}

function CompoundingTab() {
  const { compounding, fetchCompounding } = useCapabilityIntelligenceStore()

  useEffect(() => { fetchCompounding() }, [fetchCompounding])

  if (!compounding) return <div className="text-muted text-sm p-4">Loading compounding data...</div>

  const score = Number(compounding.compounding_score ?? 0)
  const velocity = Number(compounding.maturity_velocity ?? 0)
  const health = String(compounding.health ?? 'unknown')
  const byMaturity = (compounding.by_maturity ?? {}) as Record<string, number>

  const scoreColor = score >= 0.7 ? 'text-emerald-400' : score >= 0.4 ? 'text-cyan-400' : score >= 0.2 ? 'text-amber-400' : 'text-red-400'
  const velocityColor = velocity >= 0.5 ? 'text-emerald-400' : velocity >= 0.25 ? 'text-cyan-400' : 'text-amber-400'

  return (
    <div className="space-y-3">
      <SectionCard title="Compounding Score">
        <div className="flex items-center gap-4 mb-4">
          <div className="text-center">
            <div className={`text-4xl font-bold ${scoreColor}`}>{score.toFixed(2)}</div>
            <div className="text-xs text-muted mt-1">Compounding Score</div>
          </div>
          <div className="text-center">
            <div className={`text-2xl font-bold ${velocityColor}`}>{(velocity * 100).toFixed(0)}%</div>
            <div className="text-xs text-muted mt-1">Maturity Velocity</div>
          </div>
          <div className="text-center">
            <Badge label={health} variant={health} />
            <div className="text-xs text-muted mt-1">Health</div>
          </div>
        </div>

        <div className="w-full bg-zinc-800 rounded-full h-3 mb-2">
          <div
            className={`h-3 rounded-full transition-all ${
              score >= 0.7 ? 'bg-emerald-500' : score >= 0.4 ? 'bg-cyan-500' : score >= 0.2 ? 'bg-amber-500' : 'bg-red-500'
            }`}
            style={{ width: `${Math.min(score * 100, 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-muted">
          <span>0.0</span>
          <span>0.25</span>
          <span>0.50</span>
          <span>0.75</span>
          <span>1.0</span>
        </div>
      </SectionCard>

      <SectionCard title="Maturity Distribution">
        {Object.entries(byMaturity).length === 0 ? (
          <p className="text-muted text-sm">No data</p>
        ) : (
          <div className="space-y-2">
            {(['institutional', 'operational', 'validated', 'emerging'] as const).map((level) => {
              const count = byMaturity[level] ?? 0
              const total = Object.values(byMaturity).reduce((a, b) => a + b, 0)
              const pct = total > 0 ? (count / total) * 100 : 0
              return (
                <div key={level}>
                  <div className="flex items-center justify-between mb-1">
                    <Badge label={level} variant={level} />
                    <span className="text-xs font-mono text-primary">{count} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full ${
                        level === 'institutional' ? 'bg-emerald-500' :
                        level === 'operational' ? 'bg-blue-500' :
                        level === 'validated' ? 'bg-cyan-500' : 'bg-amber-500'
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </SectionCard>
    </div>
  )
}

export function CapabilitiesPanel() {
  const [activeTab, setActiveTab] = useState<Tab>('portfolio')

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border">
        <Layers size={16} className="text-cyan-400" />
        <h2 className="text-sm font-semibold text-primary">Capability Intelligence</h2>
      </div>

      <div className="flex border-b border-border px-2">
        {TABS.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'border-cyan-400 text-cyan-400'
                  : 'border-transparent text-muted hover:text-primary'
              }`}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          )
        })}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'portfolio' && <PortfolioTab />}
        {activeTab === 'gaps' && <GapsTab />}
        {activeTab === 'graph' && <GraphTab />}
        {activeTab === 'compounding' && <CompoundingTab />}
      </div>
    </div>
  )
}
