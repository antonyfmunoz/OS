import { useCallback, useRef, useState } from 'react'
import { clsx } from 'clsx'
import { useVisionStore } from '../../stores/visionStore'
import { getVisionClient } from '../../hooks/useVisionConnection'
import type { OverlayMetadata } from './VisionOverlay'

const MAX_CHIPS = 12

export function SceneInventory() {
  const overlays = useVisionStore((s) => s.overlays)
  const trackedObjects = useVisionStore((s) => s.trackedObjects)
  const connected = useVisionStore((s) => s.connected)

  // Filter out diagnostic overlays
  const realOverlays = overlays.filter((o) => !o.track_id?.startsWith('diag_'))
  const visible = realOverlays.slice(0, MAX_CHIPS)
  const overflow = realOverlays.length - MAX_CHIPS

  // Track which chips are "flashing" after long-press
  const [flashingId, setFlashingId] = useState<string | null>(null)

  const trackedLabels = new Set(trackedObjects.map((t) => t.label))

  const handleTrack = useCallback((overlay: OverlayMetadata) => {
    if (!connected) return
    getVisionClient()?.trackStart(overlay.label)
  }, [connected])

  const handleLookAt = useCallback((overlay: OverlayMetadata) => {
    if (!connected) return
    getVisionClient()?.lookAt(overlay.label)
    setFlashingId(overlay.track_id)
    setTimeout(() => setFlashingId(null), 300)
  }, [connected])

  // Long-press logic
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pointerDownPos = useRef<{ x: number; y: number } | null>(null)
  const LONG_PRESS_MS = 500
  const DRAG_THRESHOLD_PX = 10

  const startLongPress = useCallback((overlay: OverlayMetadata, x: number, y: number) => {
    pointerDownPos.current = { x, y }
    longPressTimer.current = setTimeout(() => {
      handleLookAt(overlay)
      longPressTimer.current = null
    }, LONG_PRESS_MS)
  }, [handleLookAt])

  const cancelLongPress = useCallback(() => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current)
      longPressTimer.current = null
    }
    pointerDownPos.current = null
  }, [])

  const checkDragCancel = useCallback((x: number, y: number) => {
    if (!pointerDownPos.current) return
    const dx = Math.abs(x - pointerDownPos.current.x)
    const dy = Math.abs(y - pointerDownPos.current.y)
    if (dx > DRAG_THRESHOLD_PX || dy > DRAG_THRESHOLD_PX) {
      cancelLongPress()
    }
  }, [cancelLongPress])

  if (realOverlays.length === 0) {
    return (
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono uppercase tracking-wider text-text-tertiary">
            Scene Inventory
          </span>
          <span className="text-[10px] font-mono text-text-quaternary">0 objects</span>
        </div>
        <span className="text-[10px] font-mono text-text-tertiary px-1">No objects in view</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-text-tertiary">
          Scene Inventory
        </span>
        <span className="text-[10px] font-mono text-text-quaternary">
          {realOverlays.length} object{realOverlays.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {visible.map((overlay) => {
          const isTracked = trackedLabels.has(overlay.label)
          const isFlashing = flashingId === overlay.track_id

          return (
            <button
              key={overlay.track_id}
              onClick={() => handleTrack(overlay)}
              onPointerDown={(e) => startLongPress(overlay, e.clientX, e.clientY)}
              onPointerMove={(e) => checkDragCancel(e.clientX, e.clientY)}
              onPointerUp={cancelLongPress}
              onPointerCancel={cancelLongPress}
              onPointerLeave={cancelLongPress}
              disabled={!connected}
              className={clsx(
                'flex items-center gap-1.5 px-2 py-1.5 rounded-lg border text-[11px] font-mono',
                'cursor-pointer transition-colors select-none touch-none',
                'min-h-[44px]',
                !connected && 'opacity-50 cursor-not-allowed',
                isFlashing
                  ? 'border-cyan bg-cyan/20'
                  : isTracked
                  ? 'border-cyan/30 bg-cyan/10 text-cyan'
                  : 'bg-surface-hover border-border text-text-secondary hover:border-border/80 hover:text-text-primary',
              )}
              style={{ touchAction: 'none' }}
              title="Tap to track · Long-press to look at"
            >
              {/* Color dot */}
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ background: overlay.color || '#22c55e' }}
              />
              {/* Label */}
              <span className="truncate max-w-[80px]">{overlay.label}</span>
              {/* Track ID */}
              <span className="text-[9px] text-text-quaternary shrink-0">#{overlay.track_id}</span>
              {/* Confidence */}
              <span className="text-[9px] text-text-quaternary shrink-0">
                {(overlay.confidence * 100).toFixed(0)}%
              </span>
            </button>
          )
        })}

        {overflow > 0 && (
          <span className="flex items-center px-2 py-1.5 text-[10px] font-mono text-text-tertiary">
            +{overflow} more
          </span>
        )}
      </div>
    </div>
  )
}
