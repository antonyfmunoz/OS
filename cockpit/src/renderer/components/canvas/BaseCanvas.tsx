import { useRef, useCallback, useEffect, type ReactNode } from 'react'
import { screenToCanvas, zoomAtPoint, clampZoom } from '../../utils/canvasCoords'

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

const ZOOM_FACTOR = 0.08
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

  // ── Multi-touch: two-finger pan + pinch-to-zoom ──
  const touchState = useRef<{
    startTouches: { x: number; y: number }[]
    startPanX: number
    startPanY: number
    startZoom: number
    startDist: number
  } | null>(null)

  const stateRef = useRef({ panX, panY, zoom })
  stateRef.current = { panX, panY, zoom }

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    function onWheel(e: WheelEvent) {
      e.preventDefault()
      const rect = el!.getBoundingClientRect()
      const s = stateRef.current

      if (e.ctrlKey || e.metaKey) {
        const pointX = e.clientX - rect.left
        const pointY = e.clientY - rect.top
        const factor = e.deltaY > 0 ? 1 - ZOOM_FACTOR : 1 + ZOOM_FACTOR
        const result = zoomAtPoint(s.zoom, s.zoom * factor, pointX, pointY, s.panX, s.panY)
        setPan(result.panX, result.panY)
        setZoom(result.zoom)
      } else {
        setPan(s.panX - e.deltaX, s.panY - e.deltaY)
      }
    }

    function getTouchCenter(t1: Touch, t2: Touch) {
      return { x: (t1.clientX + t2.clientX) / 2, y: (t1.clientY + t2.clientY) / 2 }
    }
    function getTouchDist(t1: Touch, t2: Touch) {
      const dx = t1.clientX - t2.clientX
      const dy = t1.clientY - t2.clientY
      return Math.sqrt(dx * dx + dy * dy)
    }

    function onTouchStart(e: TouchEvent) {
      if (e.touches.length === 2) {
        e.preventDefault()
        const t1 = e.touches[0], t2 = e.touches[1]
        const s = stateRef.current
        touchState.current = {
          startTouches: [
            { x: t1.clientX, y: t1.clientY },
            { x: t2.clientX, y: t2.clientY },
          ],
          startPanX: s.panX,
          startPanY: s.panY,
          startZoom: s.zoom,
          startDist: getTouchDist(t1, t2),
        }
      }
    }

    function onTouchMove(e: TouchEvent) {
      if (e.touches.length === 2 && touchState.current) {
        e.preventDefault()
        const ts = touchState.current
        const t1 = e.touches[0], t2 = e.touches[1]
        const rect = el!.getBoundingClientRect()

        const startCenter = {
          x: (ts.startTouches[0].x + ts.startTouches[1].x) / 2,
          y: (ts.startTouches[0].y + ts.startTouches[1].y) / 2,
        }
        const curCenter = getTouchCenter(t1, t2)
        const curDist = getTouchDist(t1, t2)

        const scale = curDist / ts.startDist
        const newZoom = clampZoom(ts.startZoom * scale)

        const pointX = startCenter.x - rect.left
        const pointY = startCenter.y - rect.top
        const result = zoomAtPoint(ts.startZoom, newZoom, pointX, pointY, ts.startPanX, ts.startPanY)

        const panDx = curCenter.x - startCenter.x
        const panDy = curCenter.y - startCenter.y

        setPan(result.panX + panDx, result.panY + panDy)
        setZoom(result.zoom)
      }
    }

    function onTouchEnd(e: TouchEvent) {
      if (e.touches.length < 2) {
        touchState.current = null
      }
    }

    el.addEventListener('wheel', onWheel, { passive: false })
    el.addEventListener('touchstart', onTouchStart, { passive: false })
    el.addEventListener('touchmove', onTouchMove, { passive: false })
    el.addEventListener('touchend', onTouchEnd)
    return () => {
      el.removeEventListener('wheel', onWheel)
      el.removeEventListener('touchstart', onTouchStart)
      el.removeEventListener('touchmove', onTouchMove)
      el.removeEventListener('touchend', onTouchEnd)
    }
  }, [setPan, setZoom])

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
        <div className="absolute bottom-12 left-1/2 -translate-x-1/2 z-10 pointer-events-auto">
          {toolbar}
        </div>
      )}
    </div>
  )
}
