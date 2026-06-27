import { useRef, useCallback, type ReactNode } from 'react'
import { screenToCanvas, zoomAtPoint } from '../../utils/canvasCoords'

interface BaseCanvasProps {
  panX: number
  panY: number
  zoom: number
  setPan: (x: number, y: number) => void
  setZoom: (zoom: number) => void
  onContextMenu?: (canvasX: number, canvasY: number, screenX: number, screenY: number) => void
  toolbar?: ReactNode
  palette?: ReactNode
  children: ReactNode
}

const ZOOM_STEP = 0.1
const DOT_SIZE = 20

export function BaseCanvas({
  panX,
  panY,
  zoom,
  setPan,
  setZoom,
  onContextMenu,
  toolbar,
  palette,
  children,
}: BaseCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const panning = useRef(false)
  const panStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 })
  const spaceHeld = useRef(false)

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return
      e.preventDefault()
      const rect = containerRef.current?.getBoundingClientRect()
      if (!rect) return
      const pointX = e.clientX - rect.left
      const pointY = e.clientY - rect.top
      const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP
      const result = zoomAtPoint(zoom, zoom + delta, pointX, pointY, panX, panY)
      setPan(result.panX, result.panY)
      setZoom(result.zoom)
    },
    [zoom, panX, panY, setPan, setZoom],
  )

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (e.button === 1 || (e.button === 0 && spaceHeld.current)) {
        e.preventDefault()
        ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
        panning.current = true
        panStart.current = { x: e.clientX, y: e.clientY, panX, panY }
      }
    },
    [panX, panY],
  )

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!panning.current) return
      const dx = e.clientX - panStart.current.x
      const dy = e.clientY - panStart.current.y
      setPan(panStart.current.panX + dx, panStart.current.panY + dy)
    },
    [setPan],
  )

  const handlePointerUp = useCallback((e: React.PointerEvent) => {
    if (!panning.current) return
    panning.current = false
    ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
  }, [])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === ' ') {
      e.preventDefault()
      spaceHeld.current = true
    }
  }, [])

  const handleKeyUp = useCallback((e: React.KeyboardEvent) => {
    if (e.key === ' ') {
      spaceHeld.current = false
    }
  }, [])

  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      if (!onContextMenu || !containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      const screenX = e.clientX - rect.left
      const screenY = e.clientY - rect.top
      const canvas = screenToCanvas(screenX, screenY, panX, panY, zoom)
      onContextMenu(canvas.x, canvas.y, e.clientX, e.clientY)
    },
    [onContextMenu, panX, panY, zoom],
  )

  const gridOffsetX = (panX % (DOT_SIZE * zoom)) / zoom
  const gridOffsetY = (panY % (DOT_SIZE * zoom)) / zoom
  const scaledDot = DOT_SIZE

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full overflow-hidden outline-none"
      style={{
        background: 'var(--color-canvas)',
        cursor: panning.current || spaceHeld.current ? 'grabbing' : 'default',
        touchAction: 'none',
      }}
      tabIndex={0}
      onWheel={handleWheel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onKeyDown={handleKeyDown}
      onKeyUp={handleKeyUp}
      onContextMenu={handleContextMenu}
    >
      {/* Dot grid background */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: `radial-gradient(circle, var(--color-border) 1px, transparent 1px)`,
          backgroundSize: `${scaledDot * zoom}px ${scaledDot * zoom}px`,
          backgroundPosition: `${panX}px ${panY}px`,
          opacity: 0.5,
        }}
      />

      {/* Transform layer — all nodes live here */}
      <div
        style={{
          transform: `translate(${panX}px, ${panY}px) scale(${zoom})`,
          transformOrigin: '0 0',
          position: 'absolute',
          top: 0,
          left: 0,
        }}
      >
        {children}
      </div>

      {/* Palette slot — floats at left edge */}
      {palette && (
        <div className="absolute top-0 left-0 h-full z-10 pointer-events-auto">
          {palette}
        </div>
      )}

      {/* Toolbar slot — floats at bottom center */}
      {toolbar && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 pointer-events-auto">
          {toolbar}
        </div>
      )}
    </div>
  )
}
