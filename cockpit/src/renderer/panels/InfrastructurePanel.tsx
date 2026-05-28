import { useSystemStore } from '../stores/systemStore'
import { useOrganismStore } from '../stores/organismStore'
import { useRealtimeStore } from '../stores/realtimeStore'
import { usePolling } from '../hooks/usePolling'
import { TopologyMap } from '../components/TopologyMap'
import { ConnectionBanner } from '../components/ConnectionBanner'

export function InfrastructurePanel() {
  const infraNodes = useSystemStore((s) => s.infraNodes)
  const meshNodes = useSystemStore((s) => s.meshNodes)
  const fetchInfra = useSystemStore((s) => s.fetchInfra)
  const fetchMeshNodes = useSystemStore((s) => s.fetchMeshNodes)
  const workloads = useOrganismStore((s) => s.workloads)
  const bottleneckStatus = useOrganismStore((s) => s.bottleneckStatus)
  const runtimeGraph = useOrganismStore((s) => s.runtimeGraph)
  const fetchWorkloads = useOrganismStore((s) => s.fetchWorkloads)
  const fetchBottlenecks = useOrganismStore((s) => s.fetchBottlenecks)
  const fetchOrganismStatus = useOrganismStore((s) => s.fetchOrganismStatus)

  const realtimeStatus = useRealtimeStore((s) => s.status)
  const cpuPercent = useRealtimeStore((s) => s.cpuPercent)
  const memoryPercent = useRealtimeStore((s) => s.memoryPercent)
  const diskPercent = useRealtimeStore((s) => s.diskPercent)
  const containers = useRealtimeStore((s) => s.containers)

  usePolling(() => { fetchInfra(); fetchMeshNodes(); fetchWorkloads(); fetchBottlenecks(); fetchOrganismStatus() },
    realtimeStatus === 'connected' ? 15000 : 10000)

  const runtimes = runtimeGraph ? Object.values(runtimeGraph.runtimes) : []

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />

      <div className="flex items-center px-4 py-3 flex-shrink-0">
        <h2 className="text-lg font-semibold text-text-primary">Infrastructure</h2>
        <span className="ml-2 text-xs text-text-tertiary">
          {meshNodes.length} mesh · {containers.length || infraNodes.length} containers · {runtimes.length} runtimes
          {workloads ? ` · ${workloads.total_runs} workloads` : ''}
        </span>
        <div className="ml-auto flex gap-3 text-[10px]">
          <span className={cpuPercent > 90 ? 'text-danger' : cpuPercent > 70 ? 'text-warn' : 'text-ok'}>
            CPU {cpuPercent.toFixed(0)}%
          </span>
          <span className={memoryPercent > 90 ? 'text-danger' : memoryPercent > 70 ? 'text-warn' : 'text-ok'}>
            RAM {memoryPercent.toFixed(0)}%
          </span>
          <span className={diskPercent > 90 ? 'text-danger' : diskPercent > 70 ? 'text-warn' : 'text-ok'}>
            DISK {diskPercent.toFixed(0)}%
          </span>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left: topology map */}
        <div className="flex-1 overflow-y-auto p-3 border-r border-border">
          <TopologyMap />
        </div>

        {/* Right: workloads + bottlenecks */}
        <div className="w-96 overflow-y-auto p-3 space-y-4 bg-canvas">
          {/* Live containers from WS */}
          {containers.length > 0 && (
            <section>
              <h3 className="wv-label mb-3">Docker Containers (live)</h3>
              <div className="space-y-1.5">
                {containers.map((c) => {
                  const isUp = c.status.toLowerCase().includes('up')
                  return (
                    <div key={c.name} className="wv-card flex items-center gap-2 px-3 py-2">
                      <span className={`w-2 h-2 rounded-full ${isUp ? 'bg-ok' : 'bg-danger'}`} />
                      <span className="text-sm text-text-primary font-mono flex-1 truncate">{c.name}</span>
                      <span className="text-[10px] text-text-tertiary truncate max-w-[40%]">{c.status}</span>
                    </div>
                  )
                })}
              </div>
            </section>
          )}

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

          {!workloads && (bottleneckStatus?.active?.length ?? 0) === 0 && containers.length === 0 && (
            <p className="text-xs text-text-tertiary">
              No operational data — {realtimeStatus === 'connected' ? 'waiting for organism tick' : 'not yet wired: WebSocket disconnected'}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
