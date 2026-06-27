import { useRef, useCallback } from 'react'

interface DragCallbacks {
  onDragStart?: (x: number, y: number) => void
  onDrag: (x: number, y: number, deltaX: number, deltaY: number) => void
  onDragEnd?: (x: number, y: number) => void
  zoom?: number
}

export function useCanvasDrag({ onDragStart, onDrag, onDragEnd, zoom = 1 }: DragCallbacks) {
  const dragging = useRef(false)
  const startPointer = useRef({ x: 0, y: 0 })
  const startPos = useRef({ x: 0, y: 0 })

  const onPointerDown = useCallback(
    (e: React.PointerEvent, currentX: number, currentY: number) => {
      if (e.button !== 0) return
      e.stopPropagation()
      ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
      dragging.current = true
      startPointer.current = { x: e.clientX, y: e.clientY }
      startPos.current = { x: currentX, y: currentY }
      onDragStart?.(currentX, currentY)
    },
    [onDragStart],
  )

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging.current) return
      const dx = (e.clientX - startPointer.current.x) / zoom
      const dy = (e.clientY - startPointer.current.y) / zoom
      const newX = startPos.current.x + dx
      const newY = startPos.current.y + dy
      onDrag(newX, newY, dx, dy)
    },
    [onDrag, zoom],
  )

  const onPointerUp = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging.current) return
      dragging.current = false
      ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
      const dx = (e.clientX - startPointer.current.x) / zoom
      const dy = (e.clientY - startPointer.current.y) / zoom
      onDragEnd?.(startPos.current.x + dx, startPos.current.y + dy)
    },
    [onDragEnd, zoom],
  )

  return { onPointerDown, onPointerMove, onPointerUp, isDragging: dragging }
}
