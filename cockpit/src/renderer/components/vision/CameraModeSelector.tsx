import { clsx } from 'clsx'
import { Crosshair, UserCheck, Bell, Bot, Shield } from 'lucide-react'
import { useVisionStore, type CameraMode, type ControlAuthority } from '../../stores/visionStore'
import { getVisionClient } from '../../hooks/useVisionConnection'

interface ModeSpec {
  id: CameraMode
  label: string
  icon: React.ReactNode
  disabledReason: (ctx: { trackerActive: boolean; hasPtzOrRoi: boolean; aiEnabled: boolean }) => string | null
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
  {
    id: 'ai_assist', label: 'AI Assist', icon: <Bot size={12} />,
    disabledReason: ({ trackerActive, hasPtzOrRoi }) => {
      if (!trackerActive) return 'Requires active tracker'
      if (!hasPtzOrRoi) return 'Requires PTZ or digital ROI'
      return null
    },
  },
]

const AUTHORITY_PRIORITY: ControlAuthority[] = ['operator', 'voice', 'ai', 'autonomous']

export function CameraModeSelector() {
  const connected = useVisionStore((s) => s.connected)
  const cameraMode = useVisionStore((s) => s.cameraMode)
  const setCameraMode = useVisionStore((s) => s.setCameraMode)
  const followMode = useVisionStore((s) => s.followMode)
  const chainHealth = useVisionStore((s) => s.chainHealth)
  const hasPtzHardware = useVisionStore((s) => s.hasPtzHardware)
  const authority = useVisionStore((s) => s.authority)
  const setAuthority = useVisionStore((s) => s.setAuthority)
  const claimAuthority = useVisionStore((s) => s.claimAuthority)
  const addNotification = useVisionStore((s) => s.addNotification)

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

    if (mode === 'ai_assist') {
      setAuthority({ aiEnabled: true })
      addNotification('info', 'AI Assist enabled', 'operator', 'AI can suggest and request camera movements — operator always overrides', 'ai governed')
    } else if (prev === 'ai_assist') {
      setAuthority({ aiEnabled: false, aiIntentDescription: '' })
      claimAuthority('operator', 'AI Assist disabled')
    }

    if (mode === 'manual') {
      claimAuthority('operator', 'Manual mode selected')
    }

    setCameraMode(mode)
  }

  return (
    <div className="flex flex-col gap-1">
      <div className={clsx('flex gap-1', !connected && 'opacity-50 cursor-not-allowed')}>
        {MODES.map(({ id, label, icon, disabledReason }) => {
          const active = cameraMode === id
          const reason = disabledReason({ trackerActive, hasPtzOrRoi, aiEnabled: authority.aiEnabled })
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
                  ? id === 'ai_assist' ? 'bg-warning/20 text-warning border border-warning/30'
                    : 'bg-cyan/20 text-cyan border border-cyan/30'
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

      {/* Authority priority indicator — always visible */}
      <div className="flex items-center gap-2 px-2">
        <Shield size={10} className="text-text-quaternary shrink-0" />
        <div className="flex items-center gap-1">
          {AUTHORITY_PRIORITY.map((level, i) => {
            const isCurrent = authority.current === level
            const labels: Record<ControlAuthority, string> = {
              operator: 'E-stop',
              voice: 'Voice',
              ai: 'AI',
              autonomous: 'Auto',
            }
            if (i === 0) {
              return (
                <span key={level} className="text-[9px] font-mono text-ok">
                  {labels[level]}
                </span>
              )
            }
            return (
              <span key={level} className="flex items-center gap-1">
                <span className="text-[9px] text-text-quaternary">{'>'}</span>
                <span className={clsx(
                  'text-[9px] font-mono',
                  isCurrent ? 'text-warning' : 'text-text-quaternary',
                )}>
                  {labels[level]}
                </span>
              </span>
            )
          })}
        </div>
        {authority.aiEnabled && authority.aiIntentDescription && (
          <span className="text-[9px] font-mono text-warning/70 truncate ml-auto">
            AI: {authority.aiIntentDescription}
          </span>
        )}
      </div>
    </div>
  )
}
