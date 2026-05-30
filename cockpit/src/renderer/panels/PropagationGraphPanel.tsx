import { useEffect, useState, useCallback } from 'react'
import { fetchApi } from '../api/client'
import { ConnectionBanner } from '../components/ConnectionBanner'
import { usePolling } from '../hooks/usePolling'

interface GraphStats {
  total_nodes: number
  total_edges: number
  node_type_counts: Record<string, number>
  edge_type_counts: Record<string, number>
  orphaned_node_count: number
  cycle_count: number
  built_at: number
  version: string
}

interface GraphNode {
  node_id: string
  node_type: string
  title: string
  status: string
  domain: string
}

interface ImpactResult {
  analysis_id: string
  source_node_id: string
  affected_nodes: {
    node_id: string
    node_type: string
    title: string
    impact_depth: number
    impact_score: number
    propagation_mode: string
    requires_validation: boolean
    requires_approval: boolean
    requires_human: boolean
    is_blocked: boolean
  }[]
  direct_impact: string[]
  indirect_impact: string[]
  impact_depth: number
  impact_radius: number
  required_waves: number
  approval_required: string[]
  human_required: string[]
  blocked_nodes: string[]
}

interface CorrespondenceProof {
  status: string
  proof: {
    scales: {
      name: string
      change_description: string
      affected_count: number
    }[]
  } | null
}

const NODE_TYPE_COLOR: Record<string, string> = {
  work_packet: 'text-cyan',
  workcell: 'text-cyan',
  roadmap_phase: 'text-ok',
  production_truth_delta: 'text-warn',
  api_route: 'text-text-secondary',
  company: 'text-ok',
  template: 'text-text-secondary',
  knowledge_model: 'text-cyan',
  outcome: 'text-ok',
}

export default function PropagationGraphPanel() {
  const [stats, setStats] = useState<GraphStats | null>(null)
  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [impact, setImpact] = useState<ImpactResult | null>(null)
  const [proof, setProof] = useState<CorrespondenceProof | null>(null)
  const [selectedNode, setSelectedNode] = useState('')
  const [error, setError] = useState('')

  const loadData = useCallback(async () => {
    try {
      const [summaryRes, nodesRes, proofRes] = await Promise.all([
        fetchApi('/organism/propagation-graph/summary'),
        fetchApi('/organism/propagation-graph/nodes'),
        fetchApi('/organism/propagation-graph/correspondence-proof'),
      ])
      if (summaryRes.ok) setStats(await summaryRes.json())
      if (nodesRes.ok) {
        const data = await nodesRes.json()
        setNodes(data.nodes || [])
      }
      if (proofRes.ok) setProof(await proofRes.json())
      setError('')
    } catch (e) {
      setError('Failed to load propagation graph data')
    }
  }, [])

  usePolling(loadData, 30000)
  useEffect(() => { loadData() }, [loadData])

  const runImpact = useCallback(async () => {
    if (!selectedNode) return
    try {
      const res = await fetchApi('/organism/propagation-graph/impact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_node_id: selectedNode,
          change_type: 'work_packet_updated',
          title: 'Manual impact analysis',
          risk_class: 'low',
        }),
      })
      if (res.ok) setImpact(await res.json())
    } catch (e) {
      setError('Impact analysis failed')
    }
  }, [selectedNode])

  return (
    <div className="p-4 space-y-4">
      <ConnectionBanner />
      <h2 className="text-lg font-bold text-text-primary">Propagation Graph</h2>
      {error && <div className="text-danger text-sm">{error}</div>}

      {/* Graph Summary */}
      {stats && (
        <div className="border border-border rounded p-3 space-y-2">
          <h3 className="text-sm font-semibold text-text-secondary">Graph Summary</h3>
          <div className="grid grid-cols-4 gap-2 text-xs">
            <div><span className="text-text-secondary">Nodes:</span> <span className="text-cyan">{stats.total_nodes}</span></div>
            <div><span className="text-text-secondary">Edges:</span> <span className="text-cyan">{stats.total_edges}</span></div>
            <div><span className="text-text-secondary">Orphaned:</span> <span className={stats.orphaned_node_count > 0 ? 'text-warn' : 'text-ok'}>{stats.orphaned_node_count}</span></div>
            <div><span className="text-text-secondary">Cycles:</span> <span className={stats.cycle_count > 0 ? 'text-danger' : 'text-ok'}>{stats.cycle_count}</span></div>
          </div>
          <div className="text-xs text-text-secondary">
            <span>Version: {stats.version}</span>
            <span className="ml-4">Built: {new Date(stats.built_at * 1000).toLocaleString()}</span>
          </div>
          {Object.keys(stats.node_type_counts).length > 0 && (
            <div className="text-xs space-y-1">
              <span className="text-text-secondary">Node types:</span>
              <div className="flex flex-wrap gap-2">
                {Object.entries(stats.node_type_counts).map(([type, count]) => (
                  <span key={type} className={NODE_TYPE_COLOR[type] || 'text-text-secondary'}>
                    {type}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Change Event Simulator */}
      <div className="border border-border rounded p-3 space-y-2">
        <h3 className="text-sm font-semibold text-text-secondary">Impact Simulator</h3>
        <div className="flex gap-2 items-center">
          <select
            value={selectedNode}
            onChange={(e) => setSelectedNode(e.target.value)}
            className="bg-bg-secondary text-text-primary text-xs p-1 rounded border border-border flex-1"
          >
            <option value="">Select source node...</option>
            {nodes.map((n) => (
              <option key={n.node_id} value={n.node_id}>
                [{n.node_type}] {n.title || n.node_id}
              </option>
            ))}
          </select>
          <button
            onClick={runImpact}
            disabled={!selectedNode}
            className="bg-cyan text-bg-primary text-xs px-3 py-1 rounded disabled:opacity-50"
          >
            Analyze
          </button>
        </div>
      </div>

      {/* Impact Analysis */}
      {impact && (
        <div className="border border-border rounded p-3 space-y-2">
          <h3 className="text-sm font-semibold text-text-secondary">Impact Analysis</h3>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div><span className="text-text-secondary">Direct:</span> <span className="text-cyan">{impact.direct_impact.length}</span></div>
            <div><span className="text-text-secondary">Indirect:</span> <span className="text-warn">{impact.indirect_impact.length}</span></div>
            <div><span className="text-text-secondary">Depth:</span> <span className="text-text-primary">{impact.impact_depth}</span></div>
            <div><span className="text-text-secondary">Waves:</span> <span className="text-text-primary">{impact.required_waves}</span></div>
            <div><span className="text-text-secondary">Approval:</span> <span className={impact.approval_required.length > 0 ? 'text-warn' : 'text-ok'}>{impact.approval_required.length}</span></div>
            <div><span className="text-text-secondary">Human:</span> <span className={impact.human_required.length > 0 ? 'text-warn' : 'text-ok'}>{impact.human_required.length}</span></div>
            <div><span className="text-text-secondary">Blocked:</span> <span className={impact.blocked_nodes.length > 0 ? 'text-danger' : 'text-ok'}>{impact.blocked_nodes.length}</span></div>
          </div>
          {impact.affected_nodes.length > 0 && (
            <div className="text-xs space-y-1 max-h-48 overflow-y-auto">
              {impact.affected_nodes.map((n) => (
                <div key={n.node_id} className="flex justify-between border-b border-border pb-1">
                  <span className={NODE_TYPE_COLOR[n.node_type] || 'text-text-secondary'}>
                    {n.title || n.node_id}
                  </span>
                  <span className="text-text-secondary">
                    d={n.impact_depth} {n.propagation_mode}
                    {n.requires_approval && ' [APPROVE]'}
                    {n.requires_human && ' [HUMAN]'}
                    {n.is_blocked && ' [BLOCKED]'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Correspondence Proof */}
      {proof && proof.proof && (
        <div className="border border-border rounded p-3 space-y-2">
          <h3 className="text-sm font-semibold text-text-secondary">Correspondence Proof</h3>
          <div className="text-xs space-y-1">
            {proof.proof.scales.map((s, i) => (
              <div key={i} className="border-b border-border pb-1">
                <span className="text-ok font-semibold">{s.name}</span>
                <span className="text-text-secondary ml-2">{s.change_description}</span>
                <span className="text-cyan ml-2">({s.affected_count} affected)</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
