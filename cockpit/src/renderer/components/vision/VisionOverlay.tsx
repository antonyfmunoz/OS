import { useVisionStore } from '../../stores/visionStore'
import { TrackedObjectBox } from './TrackedObjectBox'
import { PoseSkeletonOverlay } from './PoseSkeletonOverlay'
import { HandLandmarkOverlay } from './HandLandmarkOverlay'
import { FaceTrackingOverlay } from './FaceTrackingOverlay'

export interface OverlayMetadata {
  type: 'object' | 'face' | 'hand' | 'pose' | 'motion' | string
  track_id: string
  label: string
  confidence: number
  bbox: { x: number; y: number; w: number; h: number }
  landmarks?: Array<{ x: number; y: number; label?: string }>
  connections?: Array<[number, number]>
  color?: string
  source?: string
  model?: string
}

interface VisionOverlayProps {
  overlays?: OverlayMetadata[]
  width: number
  height: number
  visible?: boolean
}

export function VisionOverlay({ overlays = [], width, height, visible = true }: VisionOverlayProps) {
  const trackerStack = useVisionStore((s) => s.trackerStack)
  const securityMode = useVisionStore((s) => s.securityMode)
  const labelCorrections = useVisionStore((s) => s.labelCorrections)

  if (!visible) return null

  const effectiveOverlays = overlays.map((o) => {
    const correction = labelCorrections[o.track_id]
    if (correction) return { ...o, label: correction.correctedLabel }
    return o
  })

  if (effectiveOverlays.length === 0) return null

  const enabledCategories = new Set(
    trackerStack.enabled_trackers
      .filter((t) => t.enabled)
      .map((t) => t.category)
  )
  const hasTrackerFilters = enabledCategories.size > 0

  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      style={{ zIndex: 10 }}
    >
      {securityMode.active && (
        <rect
          x={0} y={0} width={width} height={height}
          fill="none" stroke="#ef4444" strokeWidth={3}
          strokeDasharray="12 6" opacity={0.6}
        />
      )}

      {effectiveOverlays.map((overlay) => {
        const typeToCategory: Record<string, string> = {
          object: 'object_detector',
          face: 'face_tracker',
          hand: 'hand_tracker',
          pose: 'pose_tracker',
          motion: 'motion_tracker',
        }
        const cat = typeToCategory[overlay.type]
        if (hasTrackerFilters && cat && !enabledCategories.has(cat)) return null

        const px = overlay.bbox.x * width
        const py = overlay.bbox.y * height
        const pw = overlay.bbox.w * width
        const ph = overlay.bbox.h * height

        switch (overlay.type) {
          case 'face':
            return (
              <FaceTrackingOverlay
                key={overlay.track_id}
                x={px} y={py} w={pw} h={ph}
                label={overlay.label}
                confidence={overlay.confidence}
                landmarks={overlay.landmarks?.map((l) => ({ x: l.x * width, y: l.y * height, label: l.label }))}
              />
            )
          case 'hand':
            return (
              <HandLandmarkOverlay
                key={overlay.track_id}
                landmarks={overlay.landmarks?.map((l) => ({ x: l.x * width, y: l.y * height, label: l.label })) || []}
                connections={overlay.connections || []}
                color={overlay.color || '#22d3ee'}
              />
            )
          case 'pose':
            return (
              <PoseSkeletonOverlay
                key={overlay.track_id}
                landmarks={overlay.landmarks?.map((l) => ({ x: l.x * width, y: l.y * height, label: l.label })) || []}
                connections={overlay.connections || []}
                color={overlay.color || '#a78bfa'}
              />
            )
          default:
            return (
              <TrackedObjectBox
                key={overlay.track_id}
                x={px} y={py} w={pw} h={ph}
                label={overlay.label}
                confidence={overlay.confidence}
                color={overlay.color || '#22c55e'}
                trackId={overlay.track_id}
              />
            )
        }
      })}
    </svg>
  )
}
