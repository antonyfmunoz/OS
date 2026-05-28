import { useOrganismStore } from '../stores/organismStore'
import { useRealtimeStore } from '../stores/realtimeStore'
import { useSystemStore } from '../stores/systemStore'

const STATUS_DOT: Record<string, string> = {
  healthy: 'bg-ok',
  available: 'bg-ok',
  online: 'bg-ok',
  running: 'bg-ok',
  connected: 'bg-ok',
  degraded: 'bg-warn',
  unavailable: 'bg-danger',
  offline: 'bg-danger',
  blocked: 'bg-danger',
  unknown: 'bg-text-tertiary',
  disconnected: 'bg-danger',
  connecting: 'bg-warn animate-pulse',
  fallback: 'bg-amber',
}

interface TopologyNode {
  id: string
  label: string
  type: string
  status: string
  detail?: string
  children?: TopologyNode[]
}

export function TopologyMap() {
  const organismStatus = useOrganismStore((s) => s.organismStatus)
  const runtimeGraph = useOrganismStore((s) => s.runtimeGraph)
  const spine = useOrganismStore((s) => s.spine)
  const guard = useOrganismStore((s) => s.guard)
  const gateway = useOrganismStore((s) => s.gateway)
  const executionMode = useOrganismStore((s) => s.executionMode)
  const realtimeStatus = useRealtimeStore((s) => s.status)
  const containers = useRealtimeStore((s) => s.containers)
  const meshNodes = useSystemStore((s) => s.meshNodes)

  const nodes: TopologyNode[] = []

  nodes.push({
    id: 'organism',
    label: 'Organism Daemon',
    type: 'core',
    status: organismStatus?.running ? 'running' : 'unavailable',
    detail: organismStatus ? `tick #${organismStatus.tick_count} · ${organismStatus.agents?.length ?? 0} agents` : undefined,
  })

  nodes.push({
    id: 'spine',
    label: 'Execution Spine',
    type: 'core',
    status: spine ? 'running' : 'unavailable',
    detail: spine ? `${spine.total_executed} executed · ${spine.registered_mutations} mutations · ${spine.current_mode}` : undefined,
  })

  nodes.push({
    id: 'gateway',
    label: 'Autonomous Gateway',
    type: 'core',
    status: gateway ? 'running' : 'unavailable',
    detail: gateway ? `${gateway.policy} · ${gateway.total_submitted} submitted` : undefined,
  })

  nodes.push({
    id: 'guard',
    label: 'Spine Guard',
    type: 'core',
    status: guard ? 'running' : 'unavailable',
    detail: guard ? `${guard.mode} · ${guard.total_allowed} allowed · ${guard.total_blocked} blocked` : undefined,
  })

  nodes.push({
    id: 'event_spine',
    label: 'EventSpine',
    type: 'core',
    status: organismStatus?.running ? 'running' : 'unavailable',
    detail: organismStatus?.supervisor_available ? 'supervisor active' : 'no supervisor',
  })

  nodes.push({
    id: 'cockpit_ws',
    label: 'Cockpit WebSocket',
    type: 'transport',
    status: realtimeStatus === 'connected' ? 'connected' : realtimeStatus === 'fallback' ? 'fallback' : 'disconnected',
    detail: realtimeStatus,
  })

  nodes.push({
    id: 'operator_api',
    label: 'Operator API',
    type: 'transport',
    status: 'running',
    detail: ':8091',
  })

  if (executionMode) {
    nodes.push({
      id: 'execution_mode',
      label: 'Execution Mode',
      type: 'governance',
      status: executionMode.reliability > 0.8 ? 'healthy' : 'degraded',
      detail: `${executionMode.current_mode} · ${(executionMode.reliability * 100).toFixed(0)}% reliable`,
    })
  }

  const runtimes = runtimeGraph ? Object.values(runtimeGraph.runtimes) : []
  if (runtimes.length > 0) {
    runtimes.forEach((r) => {
      nodes.push({
        id: `rt_${r.runtime_id}`,
        label: r.runtime_id,
        type: 'runtime',
        status: r.status,
        detail: `${r.runtime_class} · ${(r.reliability.success_rate * 100).toFixed(0)}% · ${r.reliability.avg_latency_ms.toFixed(0)}ms`,
      })
    })
  }

  if (containers.length > 0) {
    containers.forEach((c) => {
      const status = c.status.toLowerCase().includes('up') ? 'running' : 'unavailable'
      nodes.push({
        id: `docker_${c.name}`,
        label: c.name,
        type: 'docker',
        status,
        detail: c.status,
      })
    })
  }

  meshNodes.forEach((n) => {
    nodes.push({
      id: `mesh_${n.node_id}`,
      label: n.hostname,
      type: 'mesh',
      status: n.status === 'online' ? 'online' : 'offline',
      detail: `${n.role}${n.ip ? ` · ${n.ip}` : ''}`,
    })
  })

  const groups = groupBy(nodes, (n) => n.type)

  const typeLabels: Record<string, string> = {
    core: 'Core Systems',
    governance: 'Governance',
    transport: 'Transport',
    runtime: 'Runtimes',
    docker: 'Containers',
    mesh: 'Node Mesh',
  }

  const typeOrder = ['core', 'governance', 'transport', 'runtime', 'docker', 'mesh']

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="wv-label">Runtime Topology</h3>
        <span className="text-[10px] text-text-tertiary">
          {nodes.length} nodes ·{' '}
          {nodes.filter((n) => ['running', 'healthy', 'available', 'online', 'connected'].includes(n.status)).length} healthy
        </span>
      </div>

      <div className="overflow-y-auto flex-1 space-y-3">
        {typeOrder.map((type) => {
          const group = groups[type]
          if (!group || group.length === 0) return null
          return (
            <section key={type}>
              <h4 className="text-[9px] text-text-tertiary uppercase tracking-wider mb-1.5">
                {typeLabels[type] ?? type}
              </h4>
              <div className="grid grid-cols-1 gap-1">
                {group.map((node) => (
                  <div key={node.id} className="flex items-center gap-2 px-2 py-1.5 rounded bg-surface">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[node.status] ?? 'bg-text-tertiary'}`} />
                    <span className="text-[11px] text-text-primary font-mono truncate flex-1">{node.label}</span>
                    {node.detail && (
                      <span className="text-[10px] text-text-tertiary truncate max-w-[50%]">{node.detail}</span>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )
        })}
      </div>
    </div>
  )
}

function groupBy<T>(items: T[], keyFn: (item: T) => string): Record<string, T[]> {
  const result: Record<string, T[]> = {}
  for (const item of items) {
    const key = keyFn(item)
    if (!result[key]) result[key] = []
    result[key].push(item)
  }
  return result
}
