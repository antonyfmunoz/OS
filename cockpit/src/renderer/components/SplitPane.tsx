import { useState, useRef, useCallback, type ReactNode } from 'react'

interface SplitPaneProps {
  left: ReactNode
  right: ReactNode
  initialRatio?: number
  minRatio?: number
  maxRatio?: number
  direction?: 'horizontal' | 'vertical'
}

export function SplitPane({
  left,
  right,
  initialRatio = 0.5,
  minRatio = 0.2,
  maxRatio = 0.8,
  direction = 'horizontal',
}: SplitPaneProps) {
  const [ratio, setRatio] = useState(initialRatio)
  const containerRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true

    const onMouseMove = (ev: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      let newRatio: number
      if (direction === 'horizontal') {
        newRatio = (ev.clientX - rect.left) / rect.width
      } else {
        newRatio = (ev.clientY - rect.top) / rect.height
      }
      setRatio(Math.max(minRatio, Math.min(maxRatio, newRatio)))
    }

    const onMouseUp = () => {
      dragging.current = false
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }, [direction, minRatio, maxRatio])

  const isHorizontal = direction === 'horizontal'
  const leftSize = `${ratio * 100}%`
  const rightSize = `${(1 - ratio) * 100}%`

  return (
    <div
      ref={containerRef}
      className="flex overflow-hidden h-full"
      style={{ flexDirection: isHorizontal ? 'row' : 'column' }}
    >
      <div style={{ [isHorizontal ? 'width' : 'height']: leftSize }} className="overflow-hidden">
        {left}
      </div>

      <div
        onMouseDown={handleMouseDown}
        className="flex-shrink-0"
        style={{
          [isHorizontal ? 'width' : 'height']: 4,
          cursor: isHorizontal ? 'col-resize' : 'row-resize',
          background: 'var(--border)',
        }}
      />

      <div style={{ [isHorizontal ? 'width' : 'height']: rightSize }} className="overflow-hidden">
        {right}
      </div>
    </div>
  )
}
