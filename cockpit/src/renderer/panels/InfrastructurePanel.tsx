import { useSystemStore } from '../stores/systemStore'
import { usePolling } from '../hooks/usePolling'

export function InfrastructurePanel() {
  const infraNodes = useSystemStore((s) => s.infraNodes)
  const meshNodes = useSystemStore((s) => s.meshNodes)
  const fetchInfra = useSystemStore((s) => s.fetchInfra)
  const fetchMeshNodes = useSystemStore((s) => s.fetchMeshNodes)

  usePolling(() => { fetchInfra(); fetchMeshNodes() }, 10000)

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold text-text-primary">Infrastructure</h2>
        <span className="ml-2 text-xs text-text-tertiary">
          {meshNodes.length} nodes · {infraNodes.length} services
        </span>
      </div>

      <section className="mb-6">
        <h3 className="wv-label mb-3">Mesh Nodes</h3>
        <div className="grid grid-cols-2 gap-2">
          {meshNodes.map((node) => (
            <div key={node.node_id} className="wv-card flex items-center gap-2 px-3 py-2">
              <span className={`w-2 h-2 rounded-full ${node.status === 'online' ? 'bg-ok' : 'bg-danger'}`} />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-text-primary truncate">{node.hostname}</p>
                <p className="wv-label">{node.role}</p>
              </div>
            </div>
          ))}
          {meshNodes.length === 0 && (
            <p className="text-xs text-text-tertiary col-span-2">No mesh nodes connected</p>
          )}
        </div>
      </section>

      <section>
        <h3 className="wv-label mb-3">Services</h3>
        <div className="grid grid-cols-2 gap-2">
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
            <p className="text-xs text-text-tertiary col-span-2">No infrastructure data</p>
          )}
        </div>
      </section>
    </div>
  )
}
