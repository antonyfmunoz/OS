import { useState } from 'react'

interface DeviceOnboardingCardProps {
  details: Record<string, unknown>
  onApprove: (metadata: { role: string; device_type: string }) => void
  onReject: () => void
}

const ROLES = ['controller', 'executor', 'orchestrator'] as const
const DEVICE_TYPES = ['server', 'pc', 'laptop', 'tablet', 'mobile', 'unknown'] as const

const CONFIDENCE_COLOR: Record<string, string> = {
  high: 'text-ok',
  medium: 'text-warn',
  low: 'text-danger',
}

export function DeviceOnboardingCard({ details, onApprove, onReject }: DeviceOnboardingCardProps) {
  const hostname = (details.hostname as string) || 'unknown'
  const os = (details.os as string) || 'unknown'
  const cpuCores = (details.cpu_cores as number) || 0
  const ramMb = (details.ram_mb as number) || 0
  const gpu = (details.gpu as string) || ''
  const vramMb = (details.vram_mb as number) || 0
  const diskGb = (details.disk_gb as number) || 0
  const sshReachable = (details.ssh_reachable as boolean) || false
  const recommendedRole = (details.recommended_role as string) || 'controller'
  const recommendedType = (details.recommended_type as string) || 'unknown'
  const confidence = (details.confidence as string) || 'low'

  const [role, setRole] = useState(recommendedRole)
  const [deviceType, setDeviceType] = useState(recommendedType)

  return (
    <div className="space-y-3 mt-2">
      {/* Hardware specs */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="wv-card px-3 py-2">
          <span className="wv-label">OS</span>
          <p className="font-mono text-cyan">{os}</p>
        </div>
        <div className="wv-card px-3 py-2">
          <span className="wv-label">SSH</span>
          <p className={sshReachable ? 'text-ok' : 'text-danger'}>
            {sshReachable ? 'Reachable' : 'Unreachable'}
          </p>
        </div>
        {cpuCores > 0 && (
          <div className="wv-card px-3 py-2">
            <span className="wv-label">CPU</span>
            <p className="font-mono">{cpuCores} cores</p>
          </div>
        )}
        {ramMb > 0 && (
          <div className="wv-card px-3 py-2">
            <span className="wv-label">RAM</span>
            <p className="font-mono">{ramMb >= 1024 ? `${(ramMb / 1024).toFixed(1)} GB` : `${ramMb} MB`}</p>
          </div>
        )}
        {gpu && (
          <div className="wv-card px-3 py-2 col-span-2">
            <span className="wv-label">GPU</span>
            <p className="font-mono text-sm">{gpu}{vramMb > 0 ? ` (${(vramMb / 1024).toFixed(1)} GB)` : ''}</p>
          </div>
        )}
        {diskGb > 0 && (
          <div className="wv-card px-3 py-2">
            <span className="wv-label">Disk</span>
            <p className="font-mono">{diskGb} GB</p>
          </div>
        )}
      </div>

      {/* Recommendation */}
      <div className="flex items-center gap-2 text-xs">
        <span className="wv-label">Recommendation:</span>
        <span className="font-mono text-cyan">{recommendedRole}</span>
        <span className={`font-mono ${CONFIDENCE_COLOR[confidence] ?? 'text-text-tertiary'}`}>
          ({confidence})
        </span>
      </div>

      {/* Role + type override */}
      <div className="flex gap-3">
        <div className="flex-1">
          <label className="wv-label block mb-1">Role</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full text-xs px-2 py-1.5 rounded bg-surface border border-border text-text-primary"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label className="wv-label block mb-1">Device Type</label>
          <select
            value={deviceType}
            onChange={(e) => setDeviceType(e.target.value)}
            className="w-full text-xs px-2 py-1.5 rounded bg-surface border border-border text-text-primary"
          >
            {DEVICE_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => onApprove({ role, device_type: deviceType })}
          className="flex-1 px-3 py-2 text-xs font-mono uppercase rounded bg-ok text-text-inverse"
        >
          approve + provision
        </button>
        <button
          onClick={onReject}
          className="px-3 py-2 text-xs font-mono uppercase rounded bg-surface-overlay text-danger border border-border"
        >
          ignore
        </button>
      </div>
    </div>
  )
}
