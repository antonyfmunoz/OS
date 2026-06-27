import { useRef, useCallback } from 'react'

export type Edge = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw'

interface ResizeCallbacks {
  onResize: (x: number, y: number, width: number, height: number) => void
  onResizeEnd?: () => void
  minWidth?: number
  minHeight?: number
  zoom?: number
}

const CURSORS: Record<Edge, string> = {
  n: 'ns-resize',
  s: 'ns-resize',
  e: 'ew-resize',
  w: 'ew-resize',
  ne: 'nesw-resize',
  nw: 'nwse-resize',
  se: 'nwse-resize',
  sw: 'nesw-resize',
}

export function useCanvasResize({
  onResize,
  onResizeEnd,
  minWidth = 200,
  minHeight = 150,
  zoom = 1,
}: ResizeCallbacks) {
  const resizing = useRef(false)
  const edgeRef = useRef<Edge>('se')
  const startPointer = useRef({ x: 0, y: 0 })
  const startBounds = useRef({ x: 0, y: 0, width: 0, height: 0 })

  const onPointerDown = useCallback(
    (
      e: React.PointerEvent,
      edge: Edge,
      bounds: { x: number; y: number; width: number; height: number },
    ) => {
      e.stopPropagation()
      e.preventDefault()
      ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
      resizing.current = true
      edgeRef.current = edge
      startPointer.current = { x: e.clientX, y: e.clientY }
      startBounds.current = { ...bounds }
      document.body.style.cursor = CURSORS[edge]
      document.body.style.userSelect = 'none'
    },
    [],
  )

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!resizing.current) return
      const dx = (e.clientX - startPointer.current.x) / zoom
      const dy = (e.clientY - startPointer.current.y) / zoom
      const b = startBounds.current
      const edge = edgeRef.current

      let x = b.x
      let y = b.y
      let w = b.width
      let h = b.height

      if (edge.includes('e')) w = Math.max(minWidth, b.width + dx)
      if (edge.includes('w')) {
        w = Math.max(minWidth, b.width - dx)
        x = b.x + b.width - w
      }
      if (edge.includes('s')) h = Math.max(minHeight, b.height + dy)
      if (edge.includes('n')) {
        h = Math.max(minHeight, b.height - dy)
        y = b.y + b.height - h
      }

      onResize(x, y, w, h)
    },
    [onResize, minWidth, minHeight, zoom],
  )

  const onPointerUp = useCallback(
    (e: React.PointerEvent) => {
      if (!resizing.current) return
      resizing.current = false
      ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      onResizeEnd?.()
    },
    [onResizeEnd],
  )

  return { onPointerDown, onPointerMove, onPointerUp, isResizing: resizing, CURSORS }
}
