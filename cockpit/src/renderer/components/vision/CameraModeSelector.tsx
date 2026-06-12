import { clsx } from 'clsx'
import { Crosshair, UserCheck, Bell } from 'lucide-react'
import { useVisionStore, type CameraMode } from '../../stores/visionStore'
import { getVisionClient } from '../../hooks/useVisionConnection'

const MODES: { id: CameraMode; label: string; icon: React.ReactNode }[] = [
  { id: 'manual', label: 'Manual', icon: <Crosshair size={12} /> },
  { id: 'follow', label: 'Follow', icon: <UserCheck size={12} /> },
  { id: 'watch', label: 'Watch', icon: <Bell size={12} /> },
]

export function CameraModeSelector() {
  const connected = useVisionStore((s) => s.connected)
  const cameraMode = useVisionStore((s) => s.cameraMode)
  const setCameraMode = useVisionStore((s) => s.setCameraMode)
  const followMode = useVisionStore((s) => s.followMode)

  const handleSelect = (mode: CameraMode) => {
    if (!connected) return
    const prev = cameraMode

    // Side effects when leaving a mode
    if (prev === 'follow' && mode !== 'follow') {
      getVisionClient()?.followStop()
    }

    // Side effects when entering a mode
    if (mode === 'follow' && !followMode.active) {
      getVisionClient()?.followStart()
    }

    setCameraMode(mode)
  }

  return (
    <div className={clsx('flex gap-1', !connected && 'opacity-50 cursor-not-allowed')}>
      {MODES.map(({ id, label, icon }) => {
        const active = cameraMode === id
        return (
          <button
            key={id}
            onClick={() => handleSelect(id)}
            disabled={!connected}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono uppercase tracking-wider rounded-full transition-colors',
              !connected && 'cursor-not-allowed',
              active
                ? 'bg-cyan/20 text-cyan border border-cyan/30'
                : 'bg-surface-hover text-text-secondary border border-transparent hover:text-text-primary',
            )}
          >
            {icon}
            {label}
          </button>
        )
      })}
    </div>
  )
}
