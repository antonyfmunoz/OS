import { useState, useCallback, useEffect, type ReactNode } from 'react'
import { ArrowLeft, Brain, Server, Cpu, Activity, GitBranch, Circle } from 'lucide-react'
import { BaseCanvas } from './BaseCanvas'
import { CanvasToolbar } from './CanvasToolbar'
import {
  useOrganismCanvasStore,
  type TopologyNode,
  type TopologyEdge,
} from '../../stores/organismCanvasStore'
import { clampZoom } from '../../utils/canvasCoords'
import type { CanvasMode } from '../../stores/unifiedCanvasStore'

interface OrganismCanvasWorkspaceProps {
  palette?: ReactNode
  mode?: CanvasMode
  onSetMode?: (mode: CanvasMode) => void
  paletteOpen?: boolean
  onTogglePalette?: () => void
}

type OrganismFilter = 'all' | 'node' | 'service'

function nodeId(node: TopologyNode, i: number): string {
  return (node.id ?? node.node_id ?? node.role ?? `node-${i}`) as string
}

function nodeRole(node: TopologyNode): string | undefined {
  return node.role as string | undefined
}

function edgeEndpoint(edge: TopologyEdge, key: 'source' | 'target'): string | undefined {
  const direct = edge[key]
  if (typeof direct === 'string') return direct
  const alt = key === 'source' ? edge.from : edge.to
  return typeof alt === 'string' ? alt : undefined
}

function edgeType(edge: TopologyEdge): string {
  const t = edge.type ?? edge.kind ?? edge.relation
  return typeof t === 'string' ? t : 'dependency'
}

function OrganismMapOverlay() {
  const topology = useOrganismCanvasStore((s) => s.topology)
  const health = useOrganismCanvasStore((s) => s.health)
  const loading = useOrganismCanvasStore((s) => s.loading)
  const openNode = useOrganismCanvasStore((s) => s.openNode)

  const [filter, setFilter] = useState<OrganismFilter>('all')

  const nodes = topology?.nodes ?? []
  const edges = topology?.edges ?? []
  const filteredNodes = filter === 'all' ? nodes : nodes.filter((n) => n.type === filter)

  const failures = (health?.failures as unknown[]) ?? []
  const healthy = health?.healthy as boolean | undefined

  const edgeGroups = edges.reduce<Record<string, number>>((acc, edge) => {
    const t = edgeType(edge)
    acc[t] = (acc[t] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="absolute inset-0 flex items-start justify-center z-[5] pointer-events-none overflow-auto pt-12 pb-20 px-8">
      <div className="pointer-events-auto w-full max-w-[900px] flex flex-col gap-6">
        <div className="flex items-center gap-3">
          <h2 className="text-[14px] font-medium" style={{ color: 'var(--color-text-primary)' }}>
            Organism Map
          </h2>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded-full"
            style={
              healthy
                ? { background: 'rgba(34,197,94,0.2)', color: '#22c55e' }
                : { background: 'rgba(239,68,68,0.2)', color: '#ef4444' }
            }
          >
            {healthy ? 'Healthy' : `${failures.length} failures`}
          </span>
          <div className="flex-1" />
          <div className="flex gap-1">
            {(['all', 'node', 'service'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className="px-2 py-1 text-[11px] rounded"
                style={
                  filter === f
                    ? {
                        background: 'var(--color-surface-raised)',
                        color: 'var(--color-text-primary)',
                        border: '1px solid var(--color-border)',
                      }
                    : { background: 'transparent', color: 'var(--color-text-tertiary)', border: '1px solid transparent' }
                }
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}s
              </button>
            ))}
          </div>
        </div>

        {!topology && !loading ? (
          <div className="flex flex-col items-center gap-3 mt-16" style={{ color: 'var(--color-text-tertiary)' }}>
            <Brain size={32} />
            <span className="text-[13px]">No topology available</span>
            <span className="text-[11px]">The organism map could not be loaded</span>
          </div>
        ) : (
          <>
            {loading && nodes.length === 0 && (
              <div className="text-[12px]" style={{ color: 'var(--color-text-tertiary)' }}>
                Loading topology…
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {filteredNodes.map((node, i) => {
                const id = nodeId(node, i)
                const role = nodeRole(node)
                const isNode = node.type === 'node'
                return (
                  <div
                    key={id}
                    className="p-3 rounded-lg cursor-pointer"
                    style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
                    onClick={() => openNode(id)}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ background: isNode ? '#3b82f6' : '#a855f7' }}
                      />
                      <span
                        className="text-[13px] font-medium truncate"
                        style={{ color: 'var(--color-text-primary)' }}
                      >
                        {id}
                      </span>
                    </div>
                    <div className="text-[11px] mt-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
                      {node.type}
                      {role ? ` · ${role}` : ''}
                    </div>
                  </div>
                )
              })}
            </div>

            {edges.length > 0 && (
              <div
                className="p-4 rounded-lg"
                style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <GitBranch size={14} style={{ color: 'var(--color-text-secondary)' }} />
                  <span className="text-[12px] font-medium" style={{ color: 'var(--color-text-primary)' }}>
                    {edges.length} {edges.length === 1 ? 'edge' : 'edges'} across {nodes.length} entities
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(edgeGroups).map(([type, count]) => (
                    <span
                      key={type}
                      className="text-[10px] px-1.5 py-0.5 rounded"
                      style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-tertiary)' }}
                    >
                      {type} · {count}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function OrganismMapView({ palette, mode, onSetMode, paletteOpen = false, onTogglePalette }: OrganismCanvasWorkspaceProps) {
  const panX = useOrganismCanvasStore((s) => s.panX)
  const panY = useOrganismCanvasStore((s) => s.panY)
  const zoom = useOrganismCanvasStore((s) => s.zoom)
  const setPan = useOrganismCanvasStore((s) => s.setPan)
  const setZoom = useOrganismCanvasStore((s) => s.setZoom)

  const handleZoomIn = useCallback(() => setZoom(clampZoom(zoom + 0.1)), [zoom, setZoom])
  const handleZoomOut = useCallback(() => setZoom(clampZoom(zoom - 0.1)), [zoom, setZoom])
  const handleZoomReset = useCallback(() => {
    setZoom(1)
    setPan(0, 0)
  }, [setZoom, setPan])

  return (
    <>
      <BaseCanvas
        panX={panX}
        panY={panY}
        zoom={zoom}
        setPan={setPan}
        setZoom={setZoom}
        palette={palette}
        toolbar={
          <CanvasToolbar
            zoom={zoom}
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onZoomReset={handleZoomReset}
            onFitAll={() => {}}
            onTile={() => {}}
            onTogglePalette={onTogglePalette ?? (() => {})}
            paletteOpen={paletteOpen}
            mode={mode}
            onSetMode={onSetMode}
          />
        }
      >
        {null}
      </BaseCanvas>

      <OrganismMapOverlay />
    </>
  )
}

const METADATA_SKIP = new Set(['id', 'node_id', 'type', 'role', 'status'])

function OrganismNodeDetail() {
  const activeNodeId = useOrganismCanvasStore((s) => s.activeNodeId)
  const nodeDetail = useOrganismCanvasStore((s) => s.nodeDetail)
  const topology = useOrganismCanvasStore((s) => s.topology)
  const closeNode = useOrganismCanvasStore((s) => s.closeNode)

  const detail = (nodeDetail ?? {}) as Record<string, unknown>
  const type = detail.type as string | undefined
  const role = detail.role as string | undefined
  const status = detail.status as string | undefined
  const capabilities = Array.isArray(detail.capabilities) ? (detail.capabilities as unknown[]) : null

  const metadata = Object.entries(detail).filter(
    ([key, value]) =>
      !METADATA_SKIP.has(key) &&
      key !== 'capabilities' &&
      (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'),
  )

  const edges = topology?.edges ?? []
  const connected = edges.filter((edge) => {
    if (!activeNodeId) return false
    return edgeEndpoint(edge, 'source') === activeNodeId || edgeEndpoint(edge, 'target') === activeNodeId
  })

  return (
    <div className="h-full flex flex-col">
      <div
        className="flex items-center gap-2 px-3 h-8 shrink-0"
        style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-surface)' }}
      >
        <button
          onClick={closeNode}
          className="flex items-center gap-1 text-[11px]"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          <ArrowLeft size={12} /> Organism Map
        </button>
        <span className="text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>
          {activeNodeId}
        </span>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="flex flex-col gap-4 max-w-[900px] mx-auto w-full p-6">
          <div
            className="p-4 rounded-lg"
            style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
          >
            <div className="flex items-center gap-2 mb-3">
              {type === 'service' ? (
                <Server size={16} style={{ color: 'var(--color-text-secondary)' }} />
              ) : (
                <Cpu size={16} style={{ color: 'var(--color-text-secondary)' }} />
              )}
              <span className="text-[14px] font-medium" style={{ color: 'var(--color-text-primary)' }}>
                {activeNodeId}
              </span>
              {status && (
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded capitalize"
                  style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)' }}
                >
                  {status}
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-y-1 text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>
              <span>ID</span>
              <span style={{ color: 'var(--color-text-tertiary)' }}>{activeNodeId ?? '—'}</span>
              <span>Type</span>
              <span style={{ color: 'var(--color-text-tertiary)' }}>{type ?? '—'}</span>
              <span>Role</span>
              <span style={{ color: 'var(--color-text-tertiary)' }}>{role ?? '—'}</span>
              {status && (
                <>
                  <span>Status</span>
                  <span style={{ color: 'var(--color-text-tertiary)' }}>{status}</span>
                </>
              )}
              {metadata.map(([key, value]) => (
                <div key={key} className="contents">
                  <span>{key}</span>
                  <span style={{ color: 'var(--color-text-tertiary)' }}>
                    {String(value)}
                  </span>
                </div>
              ))}
            </div>

            {capabilities && capabilities.length > 0 && (
              <div className="mt-3">
                <span className="text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>
                  Capabilities
                </span>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {capabilities.map((cap, i) => (
                    <span
                      key={i}
                      className="text-[10px] px-1.5 py-0.5 rounded-full"
                      style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-tertiary)' }}
                    >
                      {String(cap)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div
            className="p-4 rounded-lg"
            style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Activity size={14} style={{ color: 'var(--color-text-secondary)' }} />
              <span className="text-[12px] font-medium" style={{ color: 'var(--color-text-primary)' }}>
                Connected Edges
              </span>
            </div>
            {connected.length === 0 ? (
              <span className="text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>
                No connected edges
              </span>
            ) : (
              <div className="flex flex-col gap-1">
                {connected.map((edge, i) => {
                  const source = edgeEndpoint(edge, 'source') ?? '?'
                  const target = edgeEndpoint(edge, 'target') ?? '?'
                  return (
                    <div
                      key={i}
                      className="flex items-center gap-2 px-2 py-1 rounded text-[11px]"
                      style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)' }}
                    >
                      <Circle size={9} style={{ color: 'var(--color-text-tertiary)' }} />
                      <span style={{ color: 'var(--color-text-tertiary)' }}>{source}</span>
                      <span style={{ color: 'var(--color-text-tertiary)' }}>→</span>
                      <span style={{ color: 'var(--color-text-tertiary)' }}>{target}</span>
                      <div className="flex-1" />
                      <span
                        className="text-[9px] px-1 py-0.5 rounded"
                        style={{ background: 'var(--color-surface)', color: 'var(--color-text-tertiary)' }}
                      >
                        {edgeType(edge)}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function OrganismCanvasWorkspace(props: OrganismCanvasWorkspaceProps) {
  const activeNodeId = useOrganismCanvasStore((s) => s.activeNodeId)

  useEffect(() => {
    useOrganismCanvasStore.getState().fetchTopology()
    useOrganismCanvasStore.getState().fetchHealth()
  }, [])

  if (activeNodeId) {
    return <OrganismNodeDetail />
  }

  return <OrganismMapView {...props} />
}
