import { useEffect, useState } from 'react'
import { useOrganismCanvasStore } from '../stores/organismCanvasStore'
import { ConnectionBanner } from '../components/ConnectionBanner'
import { usePolling } from '../hooks/usePolling'

export function OrganismMapPanel() {
  const topology = useOrganismCanvasStore((s) => s.topology)
  const health = useOrganismCanvasStore((s) => s.health)
  const selectedNode = useOrganismCanvasStore((s) => s.nodeDetail)
  const activeNodeId = useOrganismCanvasStore((s) => s.activeNodeId)
  const loading = useOrganismCanvasStore((s) => s.loading)
  const fetchTopology = useOrganismCanvasStore((s) => s.fetchTopology)
  const fetchHealth = useOrganismCanvasStore((s) => s.fetchHealth)
  const fetchNodeDetail = useOrganismCanvasStore((s) => s.fetchNodeDetail)
  const openNode = useOrganismCanvasStore((s) => s.openNode)
  const clearSelection = useOrganismCanvasStore((s) => s.closeNode)
  const [filter, setFilter] = useState<'all' | 'node' | 'service'>('all')

  useEffect(() => {
    fetchTopology()
    fetchHealth()
  }, [fetchTopology, fetchHealth])

  usePolling(() => { fetchTopology(); fetchHealth() }, 15000)

  const nodes = topology?.nodes ?? []
  const edges = topology?.edges ?? []
  const filteredNodes = filter === 'all' ? nodes : nodes.filter((n) => n.type === filter)
  const failures = (health as Record<string, unknown>)?.failures as unknown[]
  const healthy = (health as Record<string, unknown>)?.healthy as boolean

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-foreground">Organism Map</h2>
          <span className={`px-2 py-0.5 text-xs rounded-full ${healthy ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {healthy ? 'Healthy' : `${(failures ?? []).length} failures`}
          </span>
        </div>
        <div className="flex gap-1">
          {(['all', 'node', 'service'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-xs rounded ${filter === f ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}s
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4">
          {loading && nodes.length === 0 && (
            <div className="text-muted-foreground text-sm">Loading topology...</div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredNodes.map((node, i) => {
              const id = (node.id ?? node.node_id ?? node.role ?? `node-${i}`) as string
              const isSelected = activeNodeId === id
              return (
                <button
                  key={id}
                  onClick={() => { openNode(id); fetchNodeDetail(id) }}
                  className={`text-left p-3 rounded-lg border transition-colors ${isSelected ? 'border-accent bg-accent/10' : 'border-border hover:border-accent/50 bg-surface-raised'}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`w-2 h-2 rounded-full ${node.type === 'node' ? 'bg-blue-400' : 'bg-purple-400'}`} />
                    <span className="text-sm font-medium text-foreground truncate">{id}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {node.type} {node.role ? `· ${node.role}` : ''}
                  </div>
                </button>
              )
            })}
          </div>

          {edges.length > 0 && (
            <div className="mt-4 text-xs text-muted-foreground">
              {edges.length} dependencies across {nodes.length} entities
            </div>
          )}
        </div>

        {selectedNode && (
          <div className="w-80 border-l border-border overflow-y-auto p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-foreground">Detail</h3>
              <button onClick={clearSelection} className="text-xs text-muted-foreground hover:text-foreground">&times;</button>
            </div>
            <pre className="text-xs text-muted-foreground whitespace-pre-wrap break-all">
              {JSON.stringify(selectedNode, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
