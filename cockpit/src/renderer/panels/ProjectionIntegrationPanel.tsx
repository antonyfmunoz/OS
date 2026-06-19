import { useEffect, useState, useCallback } from 'react'
import {
  Puzzle,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  MapPin,
  BarChart3,
  Search,
} from 'lucide-react'
import { useProjectionIntegrationStore } from '../stores/projectionIntegrationStore'

type Tab = 'overview' | 'locations' | 'gaps' | 'readiness'

const MATURITY_COLORS: Record<string, string> = {
  seed: 'text-text-tertiary bg-surface-raised',
  prototype: 'text-yellow-400 bg-yellow-400/10',
  alpha: 'text-blue-400 bg-blue-400/10',
  beta: 'text-purple-400 bg-purple-400/10',
  production: 'text-green-400 bg-green-400/10',
}

export function ProjectionIntegrationPanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const [selectedProjection, setSelectedProjection] = useState('')
  const {
    snapshot, profiles, locations, gaps, readiness, loading,
    fetchSnapshot, fetchProfile, fetchLocations, fetchGaps, fetchReadiness,
    auditProjection,
  } = useProjectionIntegrationStore()

  useEffect(() => {
    fetchSnapshot()
  }, [])

  const projections = ((snapshot as Record<string, unknown> | null)?.projections as Record<string, unknown>[]) ?? []

  const handleSelectProjection = useCallback((id: string) => {
    setSelectedProjection(id)
    fetchProfile(id)
    fetchLocations(id)
    fetchGaps(id)
    fetchReadiness(id)
  }, [fetchProfile, fetchLocations, fetchGaps, fetchReadiness])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <Puzzle size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Projection Integration</span>
        </div>
        <button
          onClick={() => fetchSnapshot()}
          disabled={loading}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Projection selector */}
      <div className="flex gap-2 px-4 py-2 border-b border-border shrink-0 overflow-x-auto">
        {projections.map((p, i) => {
          const id = (p as Record<string, unknown>).projection_id as string ?? `proj-${i}`
          const maturity = (p as Record<string, unknown>).maturity as string ?? 'seed'
          return (
            <button
              key={i}
              onClick={() => handleSelectProjection(id)}
              className={`flex items-center gap-1.5 px-2 py-1 text-[10px] font-mono rounded border transition-colors ${
                selectedProjection === id
                  ? 'border-cyan text-cyan bg-cyan/10'
                  : 'border-border text-text-tertiary hover:text-text-secondary'
              }`}
            >
              <span className={`inline-block w-1.5 h-1.5 rounded-full ${
                maturity === 'production' ? 'bg-green-400' :
                maturity === 'beta' ? 'bg-purple-400' :
                maturity === 'alpha' ? 'bg-blue-400' :
                maturity === 'prototype' ? 'bg-yellow-400' : 'bg-text-tertiary'
              }`} />
              {(p as Record<string, unknown>).name as string ?? id}
            </button>
          )
        })}
        {projections.length === 0 && !loading && (
          <span className="text-text-tertiary text-[10px] font-mono">No projections registered</span>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border shrink-0">
        {(['overview', 'locations', 'gaps', 'readiness'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[10px] font-mono uppercase transition-colors ${
              tab === t ? 'text-cyan border-b-2 border-cyan' : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t}
            {t === 'gaps' && gaps.length > 0 && (
              <span className="ml-1 px-1 bg-orange-400/20 text-orange-400 rounded text-[9px]">{gaps.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && !snapshot && (
          <div className="text-text-tertiary text-xs font-mono">Loading projection data...</div>
        )}

        {!selectedProjection && snapshot && (
          <div className="space-y-4">
            <div className="text-text-tertiary text-xs font-mono mb-4">
              Select a projection above to view details.
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-surface-raised border border-border rounded p-3">
                <div className="text-text-tertiary text-[9px] font-mono uppercase">Projections</div>
                <div className="text-xl font-mono text-text-primary mt-1">{projections.length}</div>
              </div>
              <div className="bg-surface-raised border border-border rounded p-3">
                <div className="text-text-tertiary text-[9px] font-mono uppercase">Total Gaps</div>
                <div className="text-xl font-mono text-orange-400 mt-1">
                  {(snapshot as Record<string, unknown>).total_gaps as number ?? 0}
                </div>
              </div>
              <div className="bg-surface-raised border border-border rounded p-3">
                <div className="text-text-tertiary text-[9px] font-mono uppercase">Avg Readiness</div>
                <div className="text-xl font-mono text-cyan mt-1">
                  {(snapshot as Record<string, unknown>).avg_readiness as string ?? '—'}
                </div>
              </div>
            </div>
          </div>
        )}

        {selectedProjection && tab === 'overview' && (
          <div className="space-y-4">
            {profiles.filter((p) => (p as Record<string, unknown>).projection_id === selectedProjection).map((p, i) => {
              const maturity = (p as Record<string, unknown>).maturity as string ?? 'seed'
              return (
                <div key={i} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-mono text-text-primary">
                      {(p as Record<string, unknown>).name as string ?? selectedProjection}
                    </div>
                    <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${MATURITY_COLORS[maturity] ?? ''}`}>
                      {maturity}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-text-tertiary">
                    {(p as Record<string, unknown>).description as string ?? 'No description'}
                  </div>
                  <button
                    onClick={() => auditProjection(selectedProjection)}
                    className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20"
                  >
                    <Search size={10} /> Run Audit
                  </button>
                </div>
              )
            })}
          </div>
        )}

        {selectedProjection && tab === 'locations' && (
          <div className="space-y-2">
            {locations.map((loc, i) => (
              <div key={i} className="bg-surface-raised border border-border rounded p-3 flex items-start gap-3">
                <MapPin size={14} className="text-cyan shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-mono text-text-primary">{(loc as Record<string, unknown>).path as string ?? `Location ${i}`}</div>
                  <div className="text-[10px] font-mono text-text-tertiary mt-1">
                    Machine: {(loc as Record<string, unknown>).machine_type as string ?? 'unknown'} — {(loc as Record<string, unknown>).availability as string ?? ''}
                  </div>
                </div>
              </div>
            ))}
            {locations.length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No code locations registered for this projection</div>
            )}
          </div>
        )}

        {selectedProjection && tab === 'gaps' && (
          <div className="space-y-2">
            {gaps.map((g, i) => (
              <div key={i} className="bg-surface-raised border border-border rounded p-3 flex items-start gap-3">
                <AlertTriangle size={14} className="text-orange-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-mono text-text-primary">{(g as Record<string, unknown>).gap_type as string ?? `Gap ${i}`}</div>
                  <div className="text-[10px] font-mono text-text-tertiary mt-1">
                    {(g as Record<string, unknown>).description as string ?? ''}
                  </div>
                </div>
              </div>
            ))}
            {gaps.length === 0 && (
              <div className="flex items-center gap-2 text-green-400 text-xs font-mono">
                <CheckCircle2 size={14} />
                No integration gaps detected
              </div>
            )}
          </div>
        )}

        {selectedProjection && tab === 'readiness' && readiness && (
          <div className="space-y-4">
            <div className="bg-surface-raised border border-border rounded p-4">
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 size={14} className="text-cyan" />
                <span className="text-xs font-mono text-text-primary">Build Readiness</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(readiness as Record<string, unknown>).map(([key, val]) => (
                  <div key={key} className="text-[10px] font-mono">
                    <span className="text-text-tertiary">{key}: </span>
                    <span className="text-text-primary">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {selectedProjection && tab === 'readiness' && !readiness && !loading && (
          <div className="text-text-tertiary text-xs font-mono">No readiness data available</div>
        )}
      </div>
    </div>
  )
}
