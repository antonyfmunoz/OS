import { useState, useCallback, useEffect } from 'react'
import { BaseCanvas } from './BaseCanvas'
import { CanvasToolbar } from './CanvasToolbar'
import { CanvasContextMenu } from './CanvasContextMenu'
import { useAgentCanvasStore } from '../../stores/agentCanvasStore'
import { useAgentStore } from '../../stores/agentStore'
import { zoomAtPoint, clampZoom } from '../../utils/canvasCoords'
import { AgentCanvasNode } from './AgentCanvasNode'

export function AgentCanvasWorkspace() {
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

  return (
    <>
      <BaseCanvas
        panX={panX}
        panY={panY}
        zoom={zoom}
        setPan={setPan}
        setZoom={setZoom}
        onContextMenu={handleContextMenu}
        toolbar={
          <CanvasToolbar
            zoom={zoom}
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onZoomReset={handleZoomReset}
            onFitAll={fitAll}
            onTile={tileNodes}
            onTogglePalette={() => {}}
            paletteOpen={false}
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
