import { useState, useCallback } from 'react'
import { BaseCanvas } from './BaseCanvas'
import { CanvasWindow } from './CanvasWindow'
import { CanvasToolbar } from './CanvasToolbar'
import { CanvasPalette } from './CanvasPalette'
import { CanvasContextMenu } from './CanvasContextMenu'
import { useCanvasStore } from '../../stores/canvasStore'
import { zoomAtPoint, clampZoom } from '../../utils/canvasCoords'
import type { CanvasWindow as CanvasWindowType } from '../../stores/canvasStore'

export function CanvasWorkspace() {
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

  const [paletteOpen, setPaletteOpen] = useState(false)
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

  const handleAction = useCallback(
    (action: string) => {
      switch (action) {
        case 'tile': tileWindows(); break
        case 'fitAll': fitAll(); break
        case 'pauseAll': pauseAll(); break
        case 'resumeAll': resumeAll(); break
        case 'clearAll': clearAll(); break
      }
      setCtxMenu(null)
    },
    [tileWindows, fitAll, pauseAll, resumeAll, clearAll],
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
            onTile={tileWindows}
            onTogglePalette={() => setPaletteOpen((o) => !o)}
            paletteOpen={paletteOpen}
          />
        }
        palette={
          <CanvasPalette
            open={paletteOpen}
            onToggle={() => setPaletteOpen((o) => !o)}
            onAddWindow={handleAddWindow}
          />
        }
      >
        {windows.map((w) => (
          <CanvasWindow key={w.id} windowId={w.id} zoom={zoom} />
        ))}
      </BaseCanvas>

      <CanvasContextMenu
        x={ctxMenu?.x ?? 0}
        y={ctxMenu?.y ?? 0}
        visible={ctxMenu !== null}
        onClose={() => setCtxMenu(null)}
        onAddWindow={handleAddWindow}
        onAction={handleAction}
      />
    </>
  )
}
