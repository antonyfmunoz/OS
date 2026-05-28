import { useSystemStore } from '../stores/systemStore'
import { useOrganismStore } from '../stores/organismStore'
import { usePolling } from '../hooks/usePolling'

export function InfrastructurePanel() {
  const infraNodes = useSystemStore((s) => s.infraNodes)
  const meshNodes = useSystemStore((s) => s.meshNodes)
  const fetchInfra = useSystemStore((s) => s.fetchInfra)
  const fetchMeshNodes = useSystemStore((s) => s.fetchMeshNodes)
  const workloads = useOrganismStore((s) => s.workloads)
  const bottleneckStatus = useOrganismStore((s) => s.bottleneckStatus)
  const fetchWorkloads = useOrganismStore((s) => s.fetchWorkloads)
  const fetchBottlenecks = useOrganismStore((s) => s.fetchBottlenecks)

  usePolling(() => { fetchInfra(); fetchMeshNodes(); fetchWorkloads(); fetchBottlenecks() }, 10000)

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold text-text-primary">Infrastructure</h2>
        <span className="ml-2 text-xs text-text-tertiary">
          {meshNodes.length} nodes · {infraNodes.length} services
          {workloads ? ` · ${workloads.total_runs} workloads` : ''}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Left column */}
        <div className="space-y-4">
          <section>
            <h3 className="wv-label mb-3">Mesh Nodes</h3>
            <div className="grid grid-cols-1 gap-2">
              {meshNodes.map((node) => (
                <div key={node.node_id} className="wv-card flex items-center gap-3 px-3 py-2">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${node.status === 'online' ? 'bg-ok' : 'bg-danger'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-text-primary truncate">{node.hostname}</p>
                    <div className="flex items-center gap-2">
                      <span className="wv-label">{node.role}</span>
                      {node.os && <span className="text-[10px] text-text-tertiary">{node.os}</span>}
                    </div>
                    {node.ip && <p className="text-[10px] text-text-tertiary font-mono">{node.ip}</p>}
                  </div>
                </div>
              ))}
              {meshNodes.length === 0 && (
                <p className="text-xs text-text-tertiary">No mesh nodes connected</p>
              )}
            </div>
          </section>

          <section>
            <h3 className="wv-label mb-3">Services</h3>
            <div className="grid grid-cols-1 gap-2">
              {infraNodes.map((svc) => (
                <div key={svc.id} className="wv-card flex items-center gap-2 px-3 py-2">
                  <span className={`w-2 h-2 rounded-full ${
                    svc.status === 'healthy' ? 'bg-ok' : svc.status === 'degraded' ? 'bg-warn' : 'bg-danger'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-text-primary truncate">{svc.name}</p>
                    <p className="text-xs text-text-tertiary">{svc.type}</p>
                  </div>
                </div>
              ))}
              {infraNodes.length === 0 && (
                <p className="text-xs text-text-tertiary">No infrastructure data</p>
              )}
            </div>
          </section>
        </div>

        {/* Right column: workloads + bottlenecks */}
        <div className="space-y-4">
          {workloads && (
            <section>
              <h3 className="wv-label mb-3">
                Workload Probes — {workloads.total_runs} runs · {(workloads.success_rate * 100).toFixed(0)}% success
              </h3>
              <div className="space-y-1.5">
                {workloads.recent_outcomes.map((o, i) => (
                  <div key={i} className="wv-card flex items-center gap-2 px-3 py-2">
                    <span className={`w-2 h-2 rounded-full ${o.success ? 'bg-ok' : 'bg-danger'}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-text-primary">{o.workload_type.replace(/_/g, ' ')}</p>
                      {o.findings.length > 0 && (
                        <p className="text-[10px] text-text-tertiary truncate">{o.findings[0]}</p>
                      )}
                    </div>
                    <span className="text-[10px] text-text-tertiary font-mono">{o.duration_seconds.toFixed(1)}s</span>
                  </div>
                ))}
                {workloads.recent_outcomes.length === 0 && (
                  <p className="text-xs text-text-tertiary">No workload outcomes recorded</p>
                )}
              </div>
            </section>
          )}

          {(bottleneckStatus?.active?.length ?? 0) > 0 && (
            <section>
              <h3 className="wv-label mb-3">Bottlenecks — {bottleneckStatus!.active.length}</h3>
              <div className="space-y-1.5">
                {bottleneckStatus!.active.slice(0, 10).map((b, i) => (
                  <div key={i} className="wv-card px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono ${
                        b.severity === 'critical' || b.severity === 'high' ? 'text-danger' : 'text-warn'
                      }`}>
                        {b.severity.toUpperCase()}
                      </span>
                      <span className="text-sm text-text-primary truncate flex-1">{b.description}</span>
                    </div>
                    {b.suggested_correction && (
                      <p className="text-[10px] text-text-tertiary mt-1">fix: {b.suggested_correction}</p>
                    )}
                    <div className="flex gap-3 mt-1 text-[10px] text-text-tertiary">
                      <span>{b.source}</span>
                      <span>×{b.recurrence_count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {!workloads && (bottleneckStatus?.active?.length ?? 0) === 0 && (
            <p className="text-xs text-text-tertiary">No operational data available</p>
          )}
        </div>
      </div>
    </div>
  )
}
