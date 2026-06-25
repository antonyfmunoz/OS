import { useState } from 'react'
import { useDeviceStore } from '../stores/deviceStore'
import type { TailscalePeer, DeviceDiagnosis } from '../stores/deviceStore'
import { DeviceOnboardingCard } from './DeviceOnboardingCard'

type DiagState = 'idle' | 'diagnosing' | 'diagnosed' | 'registering' | 'registered' | 'error'

const SSH_GUIDANCE: Record<string, string> = {
  macos: 'Enable Remote Login in System Settings → General → Sharing',
  linux: 'sudo systemctl start sshd',
  windows: 'Enable OpenSSH Server in Settings → System → Optional Features',
}

interface Props {
  peer: TailscalePeer
  onRegistered: () => void
}

export function DeviceDiagnosisInline({ peer, onRegistered }: Props) {
  const diagnoseDevice = useDeviceStore((s) => s.diagnoseDevice)
  const registerDevice = useDeviceStore((s) => s.registerDevice)
  const provisionDevice = useDeviceStore((s) => s.provisionDevice)

  const [state, setState] = useState<DiagState>('idle')
  const [diagnosis, setDiagnosis] = useState<DeviceDiagnosis | null>(null)
  const [error, setError] = useState<string | null>(null)

  const ip = peer.tailscale_ips[0] ?? ''
  const displayName = peer.display_hostname || peer.dns_name || peer.hostname
  const osLower = peer.os.toLowerCase()
  const isMobile = osLower === 'ios' || osLower === 'ipados' || osLower === 'android'

  const handleDiagnose = async () => {
    setState('diagnosing')
    setError(null)
    const result = await diagnoseDevice(peer.hostname, ip, peer.os, peer.dns_name)
    if (result) {
      setDiagnosis(result)
      setState('diagnosed')
    } else {
      setError('Diagnosis failed — device may be unreachable')
      setState('error')
    }
  }

  const handleQuickAdd = async () => {
    setState('registering')
    setError(null)
    const id = peer.dns_name || peer.hostname
    const ok = await registerDevice({
      id,
      tailscale_name: peer.dns_name,
      display_name: `${peer.dns_name} (${peer.os})`,
      os: osLower,
      role: 'controller',
      device_type: isMobile ? 'mobile' : 'unknown',
      tailscale_ip: ip,
    })
    if (ok) {
      setState('registered')
      onRegistered()
    } else {
      setError('Registration failed')
      setState('error')
    }
  }

  const handleApprove = async (meta: { role: string; device_type: string }) => {
    setState('registering')
    setError(null)
    const id = peer.dns_name || peer.hostname
    const ok = await registerDevice({
      id,
      tailscale_name: peer.dns_name,
      display_name: `${peer.dns_name} (${meta.device_type})`,
      os: osLower,
      role: meta.role,
      device_type: meta.device_type,
      tailscale_ip: ip,
    })
    if (!ok) {
      setError('Registration failed')
      setState('error')
      return
    }
    if (meta.role !== 'controller') {
      await provisionDevice(id, meta.role)
    }
    setState('registered')
    onRegistered()
  }

  if (state === 'registered') {
    return (
      <div className="wv-card px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-ok" />
          <span className="text-sm text-ok">{displayName} registered</span>
        </div>
      </div>
    )
  }

  return (
    <div className="wv-card px-3 py-2">
      <div className="flex items-center gap-3">
        <span className={`w-2 h-2 rounded-full shrink-0 ${peer.online ? 'bg-ok' : 'bg-text-tertiary'}`} />
        <span className="text-sm flex-1">{displayName}</span>
        <span className="font-mono text-[10px] text-text-tertiary">{peer.os}</span>
        <span className="font-mono text-[10px] text-cyan">{ip}</span>
      </div>

      {state === 'idle' && (
        <div className="flex gap-2 mt-2">
          {!isMobile && (
            <button
              onClick={handleDiagnose}
              className="px-2 py-1 text-[10px] font-mono rounded bg-surface-overlay text-cyan border border-cyan/20"
            >
              diagnose
            </button>
          )}
          <button
            onClick={handleQuickAdd}
            className="px-2 py-1 text-[10px] font-mono rounded bg-surface-overlay text-text-secondary border border-border"
          >
            quick add{isMobile ? ' (controller)' : ''}
          </button>
        </div>
      )}

      {state === 'diagnosing' && (
        <p className="text-[10px] text-text-tertiary mt-2 animate-pulse">Diagnosing via SSH...</p>
      )}

      {state === 'registering' && (
        <p className="text-[10px] text-text-tertiary mt-2 animate-pulse">Registering...</p>
      )}

      {state === 'error' && (
        <div className="mt-2">
          <p className="text-[10px] text-danger">{error}</p>
          <button
            onClick={() => setState('idle')}
            className="text-[10px] text-text-tertiary underline mt-1"
          >
            retry
          </button>
        </div>
      )}

      {state === 'diagnosed' && diagnosis && (
        <>
          {!diagnosis.ssh_reachable && (
            <div className="mt-2 wv-card px-3 py-2 border-warn/30">
              <p className="text-[10px] text-warn">
                SSH unreachable — {SSH_GUIDANCE[osLower] || 'ensure SSH is enabled on this device'}
              </p>
            </div>
          )}
          <DeviceOnboardingCard
            details={diagnosis as unknown as Record<string, unknown>}
            onApprove={handleApprove}
            onReject={() => setState('idle')}
          />
        </>
      )}
    </div>
  )
}
