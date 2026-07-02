import { useState, useCallback, useEffect, type ReactNode } from 'react'
import { Bot, Eye } from 'lucide-react'
import { BaseCanvas } from './BaseCanvas'
import { CanvasToolbar } from './CanvasToolbar'
import { CanvasContextMenu } from './CanvasContextMenu'
import { useAgentCanvasStore } from '../../stores/agentCanvasStore'
import { useAgentStore } from '../../stores/agentStore'
import { clampZoom } from '../../utils/canvasCoords'
import { AgentCanvasNode } from './AgentCanvasNode'
import type { CanvasMode } from '../../stores/unifiedCanvasStore'

interface AgentCanvasWorkspaceProps {
  palette?: ReactNode
  mode?: CanvasMode
  onSetMode?: (mode: CanvasMode) => void
  paletteOpen?: boolean
  onTogglePalette?: () => void
}

export function AgentCanvasWorkspace({ palette, mode, onSetMode, paletteOpen = false, onTogglePalette }: AgentCanvasWorkspaceProps) {
  const nodes = useAgentCanvasStore((s) => s.nodes)
  const panX = useAgentCanvasStore((s) => s.panX)
  const panY = useAgentCanvasStore((s) => s.panY)
  const zoom = useAgentCanvasStore((s) => s.zoom)
  const setPan = useAgentCanvasStore((s) => s.setPan)
  const setZoom = useAgentCanvasStore((s) => s.setZoom)
  const fitAll = useAgentCanvasStore((s) => s.fitAll)
  const tileNodes = useAgentCanvasStore((s) => s.tileNodes)
  const syncAgents = useAgentCanvasStore((s) => s.syncAgents)
  const showAll = useAgentCanvasStore((s) => s.showAll)
  const dismissAgent = useAgentCanvasStore((s) => s.dismissAgent)

  const agents = useAgentStore((s) => s.agents)
  const fetchAgents = useAgentStore((s) => s.fetchAgents)

  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number } | null>(null)

  useEffect(() => {
    if (agents.length === 0) fetchAgents()
  }, [agents.length, fetchAgents])

  useEffect(() => {
    if (agents.length > 0) {
      syncAgents(agents.map((a) => ({ id: a.id, name: a.name, status: a.status })))
    }
  }, [agents, syncAgents])

  const handleContextMenu = useCallback(
    (_canvasX: number, _canvasY: number, screenX: number, screenY: number) => {
      setCtxMenu({ x: screenX, y: screenY })
    },
    [],
  )

  const handleAction = useCallback(
    (action: string) => {
      switch (action) {
        case 'tile': tileNodes(); break
        case 'fitAll': fitAll(); break
        case 'showAll': showAll(); break
      }
      setCtxMenu(null)
    },
    [tileNodes, fitAll, showAll],
  )

  const handleZoomIn = useCallback(() => setZoom(clampZoom(zoom + 0.1)), [zoom, setZoom])
  const handleZoomOut = useCallback(() => setZoom(clampZoom(zoom - 0.1)), [zoom, setZoom])
  const handleZoomReset = useCallback(() => {
    setZoom(1)
    setPan(0, 0)
  }, [setZoom, setPan])

  const hasDismissed = useAgentCanvasStore((s) => s.dismissedAgentIds.length > 0)

  return (
    <>
      <BaseCanvas
        panX={panX}
        panY={panY}
        zoom={zoom}
        setPan={setPan}
        setZoom={setZoom}
        onContextMenu={handleContextMenu}
        palette={palette}
        toolbar={
          <CanvasToolbar
            zoom={zoom}
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onZoomReset={handleZoomReset}
            onTogglePalette={onTogglePalette ?? (() => {})}
            paletteOpen={paletteOpen}
            mode={mode}
            onSetMode={onSetMode}
            extraButtons={
              hasDismissed ? (
                <button
                  onClick={showAll}
                  title="Show all dismissed agents"
                  className="flex items-center gap-1 px-2 py-1 rounded text-[11px]"
                  style={{ color: 'var(--color-text-secondary)' }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = 'var(--color-text-primary)'
                    e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = 'var(--color-text-secondary)'
                    e.currentTarget.style.background = 'transparent'
                  }}
                >
                  <Eye size={12} />
                  Show All
                </button>
              ) : undefined
            }
          />
        }
      >
        {nodes.map((node) => (
          <AgentCanvasNode
            key={node.agentId}
            node={node}
            zoom={zoom}
            onDismiss={dismissAgent}
          />
        ))}
      </BaseCanvas>

      {nodes.length === 0 && (
        <div
          className="absolute inset-0 flex flex-col items-center justify-center gap-3 pointer-events-none"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          <Bot size={32} />
          <span className="text-[13px]">
            {agents.length === 0 ? 'No agents registered' : 'All agents hidden'}
          </span>
          {agents.length === 0 && (
            <span className="text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>
              Agents appear automatically when registered via the API
            </span>
          )}
          {hasDismissed && (
            <button
              onClick={showAll}
              className="pointer-events-auto text-[12px] px-3 py-1.5 rounded"
              style={{
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-secondary)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-surface-overlay)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
              }}
            >
              Show All Agents
            </button>
          )}
        </div>
      )}

      {ctxMenu && (
        <CanvasContextMenu
          x={ctxMenu.x}
          y={ctxMenu.y}
          visible
          onClose={() => setCtxMenu(null)}
          onAddWindow={() => {}}
          onAction={handleAction}
        />
      )}
    </>
  )
}
