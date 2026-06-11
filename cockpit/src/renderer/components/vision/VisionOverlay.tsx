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

const SYNTHETIC_DIAG_OVERLAYS: OverlayMetadata[] = [
  {
    type: 'object',
    track_id: 'diag_tl',
    label: 'DIAG TL',
    confidence: 1.0,
    bbox: { x: 0.02, y: 0.02, w: 0.18, h: 0.12 },
    color: '#22d3ee',
  },
  {
    type: 'object',
    track_id: 'diag_tr',
    label: 'DIAG TR',
    confidence: 1.0,
    bbox: { x: 0.80, y: 0.02, w: 0.18, h: 0.12 },
    color: '#f59e0b',
  },
  {
    type: 'object',
    track_id: 'diag_center',
    label: 'PIPELINE OK',
    confidence: 1.0,
    bbox: { x: 0.35, y: 0.38, w: 0.30, h: 0.18 },
    color: '#22c55e',
  },
  {
    type: 'object',
    track_id: 'diag_bl',
    label: 'DIAG BL',
    confidence: 1.0,
    bbox: { x: 0.02, y: 0.80, w: 0.18, h: 0.12 },
    color: '#a78bfa',
  },
  {
    type: 'object',
    track_id: 'diag_br',
    label: 'DIAG BR',
    confidence: 1.0,
    bbox: { x: 0.80, y: 0.80, w: 0.18, h: 0.12 },
    color: '#f43f5e',
  },
]

interface VisionOverlayProps {
  overlays?: OverlayMetadata[]
  width: number
  height: number
  visible?: boolean
}

export function VisionOverlay({ overlays = [], width, height, visible = true }: VisionOverlayProps) {
  const trackerStack = useVisionStore((s) => s.trackerStack)
  const securityMode = useVisionStore((s) => s.securityMode)
  const diagnosticOverlay = useVisionStore((s) => s.diagnosticOverlay)

  if (!visible && !diagnosticOverlay) return null

  const realOverlays = overlays.filter(o => !o.track_id?.startsWith('diag_'))
  const diagOverlays = diagnosticOverlay ? SYNTHETIC_DIAG_OVERLAYS : []

  const effectiveOverlays: OverlayMetadata[] = []

  if (visible) {
    effectiveOverlays.push(...realOverlays)
  }

  if (diagnosticOverlay) {
    effectiveOverlays.push(...diagOverlays)
  }

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
        const isDiagnostic = overlay.track_id?.startsWith('diag_')

        const typeToCategory: Record<string, string> = {
          object: 'object_detector',
          face: 'face_tracker',
          hand: 'hand_tracker',
          pose: 'pose_tracker',
          motion: 'motion_tracker',
        }
        const cat = typeToCategory[overlay.type]
        if (!isDiagnostic && hasTrackerFilters && cat && !enabledCategories.has(cat)) return null

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
              />
            )
        }
      })}
    </svg>
  )
}
