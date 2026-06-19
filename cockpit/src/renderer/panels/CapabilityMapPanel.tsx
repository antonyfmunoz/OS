import { useEffect, useState } from 'react'
import {
  Map,
  CheckCircle2,
  AlertTriangle,
  Copy,
  RefreshCw,
} from 'lucide-react'
import { useCapabilityMapStore } from '../stores/capabilityMapStore'

type Tab = 'overview' | 'surfaces' | 'gaps' | 'duplications'

export function CapabilityMapPanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const { snapshot, mvpGaps, duplications, loading, fetchSnapshot, fetchMvpGaps, fetchDuplications } =
    useCapabilityMapStore()

  useEffect(() => {
    fetchSnapshot()
    fetchMvpGaps()
    fetchDuplications()
  }, [])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 h-9 shrink-0">
        <div className="flex items-center gap-2">
          <Map size={14} className="text-cyan" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider">Capability Map</span>
        </div>
        <button
          onClick={() => { fetchSnapshot(); fetchMvpGaps(); fetchDuplications() }}
          disabled={loading}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono uppercase bg-cyan/10 text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-50"
        >
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border shrink-0">
        {(['overview', 'surfaces', 'gaps', 'duplications'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[10px] font-mono uppercase transition-colors ${
              tab === t ? 'text-cyan border-b-2 border-cyan' : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t}
            {t === 'gaps' && mvpGaps.length > 0 && (
              <span className="ml-1 px-1 bg-orange-400/20 text-orange-400 rounded text-[9px]">{mvpGaps.length}</span>
            )}
            {t === 'duplications' && duplications.length > 0 && (
              <span className="ml-1 px-1 bg-yellow-400/20 text-yellow-400 rounded text-[9px]">{duplications.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && !snapshot && (
          <div className="text-text-tertiary text-xs font-mono">Loading capability map...</div>
        )}

        {tab === 'overview' && snapshot && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              {(['total_routes', 'total_panels', 'total_stores'] as const).map((k) => (
                <div key={k} className="bg-surface-raised border border-border rounded p-3">
                  <div className="text-text-tertiary text-[9px] font-mono uppercase">{k.replace('total_', '')}</div>
                  <div className="text-xl font-mono text-text-primary mt-1">
                    {(snapshot as Record<string, unknown>)[k] as number ?? '—'}
                  </div>
                </div>
              ))}
            </div>
            <div className="bg-surface-raised border border-border rounded p-3">
              <div className="text-text-tertiary text-[9px] font-mono uppercase mb-2">Coverage Summary</div>
              <div className="text-xs font-mono text-text-secondary whitespace-pre-wrap">
                {JSON.stringify((snapshot as Record<string, unknown>).summary ?? {}, null, 2)}
              </div>
            </div>
          </div>
        )}

        {tab === 'surfaces' && snapshot && (
          <div className="space-y-2">
            {(((snapshot as Record<string, unknown>).surfaces as Record<string, unknown>[]) ?? []).map((s, i) => (
              <div key={i} className="bg-surface-raised border border-border rounded p-3 flex items-start justify-between">
                <div>
                  <div className="text-xs font-mono text-text-primary">{(s as Record<string, unknown>).name as string ?? `Surface ${i}`}</div>
                  <div className="text-[10px] font-mono text-text-tertiary mt-1">
                    {(s as Record<string, unknown>).category as string ?? 'uncategorized'}
                  </div>
                </div>
                <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${
                  (s as Record<string, unknown>).coverage === 'full'
                    ? 'bg-green-400/10 text-green-400'
                    : 'bg-orange-400/10 text-orange-400'
                }`}>
                  {(s as Record<string, unknown>).coverage as string ?? 'unknown'}
                </span>
              </div>
            ))}
            {(((snapshot as Record<string, unknown>).surfaces as unknown[]) ?? []).length === 0 && (
              <div className="text-text-tertiary text-xs font-mono">No surfaces registered</div>
            )}
          </div>
        )}

        {tab === 'gaps' && (
          <div className="space-y-2">
            {mvpGaps.map((g, i) => (
              <div key={i} className="bg-surface-raised border border-border rounded p-3 flex items-start gap-3">
                <AlertTriangle size={14} className="text-orange-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-mono text-text-primary">{(g as Record<string, unknown>).panel as string ?? `Gap ${i}`}</div>
                  <div className="text-[10px] font-mono text-text-tertiary mt-1">
                    {(g as Record<string, unknown>).reason as string ?? 'Missing capability'}
                  </div>
                </div>
              </div>
            ))}
            {mvpGaps.length === 0 && (
              <div className="flex items-center gap-2 text-green-400 text-xs font-mono">
                <CheckCircle2 size={14} />
                No MVP gaps — all required panels present
              </div>
            )}
          </div>
        )}

        {tab === 'duplications' && (
          <div className="space-y-2">
            {duplications.map((d, i) => (
              <div key={i} className="bg-surface-raised border border-border rounded p-3 flex items-start gap-3">
                <Copy size={14} className="text-yellow-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-mono text-text-primary">
                    {(d as Record<string, unknown>).surface_a as string} / {(d as Record<string, unknown>).surface_b as string}
                  </div>
                  <div className="text-[10px] font-mono text-text-tertiary mt-1">
                    {(d as Record<string, unknown>).overlap as string ?? 'Overlapping functionality'}
                  </div>
                </div>
              </div>
            ))}
            {duplications.length === 0 && (
              <div className="flex items-center gap-2 text-green-400 text-xs font-mono">
                <CheckCircle2 size={14} />
                No duplications detected
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
