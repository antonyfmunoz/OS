import { useState, useCallback, type ReactNode } from 'react'
import { BaseCanvas } from './BaseCanvas'
import { CanvasWindow } from './CanvasWindow'
import { CanvasToolbar } from './CanvasToolbar'
import { CanvasContextMenu } from './CanvasContextMenu'
import { useCanvasStore } from '../../stores/canvasStore'
import { clampZoom } from '../../utils/canvasCoords'
import type { CanvasWindow as CanvasWindowType } from '../../stores/canvasStore'
import type { CanvasMode } from '../../stores/unifiedCanvasStore'

interface CanvasWorkspaceProps {
  palette?: ReactNode
  mode?: CanvasMode
  onSetMode?: (mode: CanvasMode) => void
  paletteOpen?: boolean
  onTogglePalette?: () => void
}

export function CanvasWorkspace({ palette, mode, onSetMode, paletteOpen = false, onTogglePalette }: CanvasWorkspaceProps) {
  const windows = useCanvasStore((s) => s.windows)
  const panX = useCanvasStore((s) => s.panX)
  const panY = useCanvasStore((s) => s.panY)
  const zoom = useCanvasStore((s) => s.zoom)
  const setPan = useCanvasStore((s) => s.setPan)
  const setZoom = useCanvasStore((s) => s.setZoom)
  const addWindow = useCanvasStore((s) => s.addWindow)
  const fitAll = useCanvasStore((s) => s.fitAll)
  const tileWindows = useCanvasStore((s) => s.tileWindows)
  const clearAll = useCanvasStore((s) => s.clearAll)
  const pauseAll = useCanvasStore((s) => s.pauseAll)
  const resumeAll = useCanvasStore((s) => s.resumeAll)
  const createCluster = useCanvasStore((s) => s.createCluster)
  const dissolveCluster = useCanvasStore((s) => s.dissolveCluster)
  const removeFromCluster = useCanvasStore((s) => s.removeFromCluster)

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; canvasX: number; canvasY: number } | null>(null)

  const handleContextMenu = useCallback(
    (canvasX: number, canvasY: number, screenX: number, screenY: number) => {
      setCtxMenu({ x: screenX, y: screenY, canvasX, canvasY })
    },
    [],
  )

  const handleAddWindow = useCallback(
    (type: string, config?: Record<string, string>) => {
      addWindow(type as CanvasWindowType['type'], config)
      setCtxMenu(null)
    },
    [addWindow],
  )

  const handleSelectWindow = useCallback((windowId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(windowId)) next.delete(windowId)
      else next.add(windowId)
      return next
    })
  }, [])

  const handleAction = useCallback(
    (action: string) => {
      switch (action) {
        case 'tile': tileWindows(); break
        case 'fitAll': fitAll(); break
        case 'pauseAll': pauseAll(); break
        case 'resumeAll': resumeAll(); break
        case 'clearAll': clearAll(); break
        case 'createCluster':
          if (selectedIds.size >= 2) {
            createCluster('Cluster', Array.from(selectedIds))
            setSelectedIds(new Set())
          }
          break
        case 'removeFromCluster': {
          selectedIds.forEach((id) => removeFromCluster(id))
          setSelectedIds(new Set())
          break
        }
        case 'dissolveCluster': {
          const win = windows.find((w) => selectedIds.has(w.id) && w.clusterId)
          if (win?.clusterId) dissolveCluster(win.clusterId)
          setSelectedIds(new Set())
          break
        }
      }
      setCtxMenu(null)
    },
    [tileWindows, fitAll, pauseAll, resumeAll, clearAll, createCluster, dissolveCluster, removeFromCluster, selectedIds, windows],
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
            onTogglePalette={onTogglePalette ?? (() => {})}
            paletteOpen={paletteOpen}
            mode={mode}
            onSetMode={onSetMode}
          />
        }
        palette={palette}
      >
        {windows.map((w) => (
          <CanvasWindow key={w.id} windowId={w.id} zoom={zoom} selected={selectedIds.has(w.id)} onSelect={handleSelectWindow} />
        ))}
      </BaseCanvas>

      <CanvasContextMenu
        x={ctxMenu?.x ?? 0}
        y={ctxMenu?.y ?? 0}
        visible={ctxMenu !== null}
        onClose={() => setCtxMenu(null)}
        onAddWindow={handleAddWindow}
        onAction={handleAction}
        selectedCount={selectedIds.size}
        targetClusterId={(() => {
          const sel = Array.from(selectedIds)
          const win = windows.find((w) => sel.includes(w.id) && w.clusterId)
          return win?.clusterId ?? null
        })()}
      />
    </>
  )
}
