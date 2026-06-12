import { clsx } from 'clsx'
import { Crosshair, UserCheck, Bell } from 'lucide-react'
import { useVisionStore, type CameraMode } from '../../stores/visionStore'
import { getVisionClient } from '../../hooks/useVisionConnection'

interface ModeSpec {
  id: CameraMode
  label: string
  icon: React.ReactNode
  disabledReason: (ctx: { trackerActive: boolean; hasPtzOrRoi: boolean }) => string | null
}

const MODES: ModeSpec[] = [
  {
    id: 'manual', label: 'Manual', icon: <Crosshair size={12} />,
    disabledReason: () => null,
  },
  {
    id: 'follow', label: 'Follow', icon: <UserCheck size={12} />,
    disabledReason: ({ trackerActive, hasPtzOrRoi }) => {
      if (!trackerActive) return 'Requires active tracker'
      if (!hasPtzOrRoi) return 'Requires PTZ or digital ROI'
      return null
    },
  },
  {
    id: 'watch', label: 'Watch', icon: <Bell size={12} />,
    disabledReason: ({ trackerActive }) =>
      trackerActive ? null : 'Requires active tracker',
  },
]

export function CameraModeSelector() {
  const connected = useVisionStore((s) => s.connected)
  const cameraMode = useVisionStore((s) => s.cameraMode)
  const setCameraMode = useVisionStore((s) => s.setCameraMode)
  const followMode = useVisionStore((s) => s.followMode)
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const hasPtzHardware = useVisionStore((s) => s.hasPtzHardware)

  const trackerActive = chainHealth.detectorStatus?.tracker_active ?? false
  const hasPtzOrRoi = hasPtzHardware || chainHealth.digitalRoiAvailable

  const handleSelect = (mode: CameraMode) => {
    if (!connected) return
    const prev = cameraMode

    if (prev === 'follow' && mode !== 'follow') {
      getVisionClient()?.followStop()
    }

    if (mode === 'follow' && !followMode.active) {
      getVisionClient()?.followStart()
    }

    setCameraMode(mode)
  }

  return (
    <div className={clsx('flex gap-1', !connected && 'opacity-50 cursor-not-allowed')}>
      {MODES.map(({ id, label, icon, disabledReason }) => {
        const active = cameraMode === id
        const reason = disabledReason({ trackerActive, hasPtzOrRoi })
        const disabled = !connected || !!reason
        return (
          <button
            key={id}
            onClick={() => handleSelect(id)}
            disabled={disabled}
            title={reason || undefined}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono uppercase tracking-wider rounded-full transition-colors',
              disabled && 'cursor-not-allowed opacity-50',
              active
                ? 'bg-cyan/20 text-cyan border border-cyan/30'
                : disabled
                  ? 'bg-surface-hover text-text-quaternary border border-transparent'
                  : 'bg-surface-hover text-text-secondary border border-transparent hover:text-text-primary',
            )}
          >
            {icon}
            {label}
            {reason && <span className="text-[8px] lowercase tracking-normal opacity-70">n/a</span>}
          </button>
        )
      })}
    </div>
  )
}
