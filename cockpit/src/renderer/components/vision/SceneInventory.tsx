import { useCallback, useRef, useState } from 'react'
import { clsx } from 'clsx'
import { Pencil, X, Check } from 'lucide-react'
import { useVisionStore } from '../../stores/visionStore'
import { getVisionClient } from '../../hooks/useVisionConnection'
import type { OverlayMetadata } from './VisionOverlay'

const MAX_CHIPS = 12

export function SceneInventory() {
  const overlays = useVisionStore((s) => s.overlays)
  const trackedObjects = useVisionStore((s) => s.trackedObjects)
  const connected = useVisionStore((s) => s.connected)
  const labelCorrections = useVisionStore((s) => s.labelCorrections)
  const setLabelCorrection = useVisionStore((s) => s.setLabelCorrection)
  const removeLabelCorrection = useVisionStore((s) => s.removeLabelCorrection)
  const addToast = useVisionStore((s) => s.addToast)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')

  const realOverlays = overlays.filter((o) => !o.track_id?.startsWith('diag_'))
  const visible = realOverlays.slice(0, MAX_CHIPS)
  const overflow = realOverlays.length - MAX_CHIPS

  const [flashingId, setFlashingId] = useState<string | null>(null)

  const trackedLabels = new Set(trackedObjects.map((t) => t.label))

  const getDisplayLabel = useCallback((overlay: OverlayMetadata): string => {
    const correction = labelCorrections[overlay.track_id]
    return correction ? correction.correctedLabel : overlay.label
  }, [labelCorrections])

  const handleTrack = useCallback((overlay: OverlayMetadata) => {
    if (!connected) return
    getVisionClient()?.trackStart(getDisplayLabel(overlay))
  }, [connected, getDisplayLabel])

  const handleLookAt = useCallback((overlay: OverlayMetadata) => {
    if (!connected) return
    getVisionClient()?.lookAt(overlay.label)
    setFlashingId(overlay.track_id)
    setTimeout(() => setFlashingId(null), 300)
  }, [connected])

  const startEdit = useCallback((overlay: OverlayMetadata) => {
    setEditingId(overlay.track_id)
    setEditValue(getDisplayLabel(overlay))
  }, [getDisplayLabel])

  const submitEdit = useCallback((overlay: OverlayMetadata) => {
    const trimmed = editValue.trim()
    if (!trimmed || trimmed === overlay.label) {
      removeLabelCorrection(overlay.track_id)
      addToast(`Label reset to "${overlay.label}"`, 'cyan')
    } else {
      setLabelCorrection(overlay.track_id, trimmed, overlay.label)
      getVisionClient()?.correctLabel(overlay.track_id, trimmed, overlay.label)
      addToast(`Relabeled "${overlay.label}" → "${trimmed}"`, 'ok')
    }
    setEditingId(null)
    setEditValue('')
  }, [editValue, setLabelCorrection, removeLabelCorrection, addToast])

  const cancelEdit = useCallback(() => {
    setEditingId(null)
    setEditValue('')
  }, [])

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
          {Object.keys(labelCorrections).length > 0 && (
            <span className="ml-1 text-warning">
              ({Object.keys(labelCorrections).length} corrected)
            </span>
          )}
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {visible.map((overlay) => {
          const isTracked = trackedLabels.has(overlay.label)
          const isFlashing = flashingId === overlay.track_id
          const isEditing = editingId === overlay.track_id
          const isCorrected = !!labelCorrections[overlay.track_id]
          const displayLabel = getDisplayLabel(overlay)

          if (isEditing) {
            return (
              <div
                key={overlay.track_id}
                className="flex items-center gap-1 px-2 py-1 rounded-lg border border-cyan/50 bg-surface min-h-[44px]"
              >
                <input
                  type="text"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') submitEdit(overlay)
                    if (e.key === 'Escape') cancelEdit()
                  }}
                  autoFocus
                  className="w-24 px-1.5 py-0.5 rounded bg-surface-hover border border-border text-[11px] font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
                  placeholder={overlay.label}
                />
                <button
                  onClick={() => submitEdit(overlay)}
                  className="p-1 rounded text-ok hover:bg-ok/10"
                >
                  <Check size={12} />
                </button>
                <button
                  onClick={cancelEdit}
                  className="p-1 rounded text-danger hover:bg-danger/10"
                >
                  <X size={12} />
                </button>
              </div>
            )
          }

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
                'group flex items-center gap-1.5 px-2 py-1.5 rounded-lg border text-[11px] font-mono',
                'cursor-pointer transition-colors select-none touch-none',
                'min-h-[44px]',
                !connected && 'opacity-50 cursor-not-allowed',
                isFlashing
                  ? 'border-cyan bg-cyan/20'
                  : isTracked
                  ? 'border-cyan/30 bg-cyan/10 text-cyan'
                  : isCorrected
                  ? 'border-warning/30 bg-warning/5 text-text-secondary'
                  : 'bg-surface-hover border-border text-text-secondary hover:border-border/80 hover:text-text-primary',
              )}
              style={{ touchAction: 'none' }}
              title={isCorrected
                ? `Corrected: "${overlay.label}" → "${displayLabel}". Tap=track · Long-press=look at · Pencil=edit`
                : 'Tap to track · Long-press to look at'}
            >
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ background: isCorrected ? '#f59e0b' : overlay.color || '#22c55e' }}
              />
              <span className="truncate max-w-[80px]">{displayLabel}</span>
              {isCorrected && (
                <span className="text-[9px] text-text-quaternary line-through shrink-0">{overlay.label}</span>
              )}
              <span className="text-[9px] text-text-quaternary shrink-0">#{overlay.track_id}</span>
              <span className="text-[9px] text-text-quaternary shrink-0">
                {(overlay.confidence * 100).toFixed(0)}%
              </span>
              <button
                onClick={(e) => { e.stopPropagation(); startEdit(overlay) }}
                className="hidden group-hover:block p-0.5 rounded text-text-quaternary hover:text-cyan shrink-0"
                title="Relabel this object"
              >
                <Pencil size={10} />
              </button>
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
