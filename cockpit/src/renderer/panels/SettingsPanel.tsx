import { useState } from 'react'
import { useSettingsStore } from '../stores/settingsStore'
import { useDeviceStore } from '../stores/deviceStore'
import type { TailscalePeer } from '../stores/deviceStore'
import { usePolling } from '../hooks/usePolling'
import { DeviceDiagnosisInline } from '../components/DeviceDiagnosisInline'

const AUTHORITY_COLORS: Record<string, string> = {
  AUTONOMOUS: 'text-ok',
  APPROVE: 'text-warn',
  DENY: 'text-danger',
}

export function SettingsPanel() {
  const settings = useSettingsStore((s) => s.settings)
  const governance = useSettingsStore((s) => s.governance)
  const fetchSettings = useSettingsStore((s) => s.fetchSettings)
  const fetchGovernance = useSettingsStore((s) => s.fetchGovernance)

  usePolling(() => {
    fetchSettings()
    fetchGovernance()
  }, 30000)

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      <h2 className="text-lg font-semibold">System Configuration</h2>

      {/* Model Routing */}
      <section>
        <h3 className="wv-label mb-3">Model Routing</h3>
        {settings?.model_routing ? (
          <div className="space-y-1.5">
            {settings.model_routing.map((route) => (
              <div key={route.provider} className="wv-card flex items-center gap-3 px-3 py-2">
                <span className={`w-2 h-2 rounded-full shrink-0 ${route.available ? 'bg-ok' : 'bg-text-tertiary'}`} />
                <div className="flex-1 min-w-0">
                  <span className="text-sm">{route.provider}</span>
                  {route.model_id && (
                    <span className="text-[10px] text-text-tertiary ml-2">{route.model_id}</span>
                  )}
                </div>
                {route.role && (
                  <span className="font-mono text-[10px] text-warn">{route.role}</span>
                )}
                {route.quality != null && route.quality > 0 && (
                  <span className="font-mono text-[10px] text-text-secondary">Q{route.quality}</span>
                )}
                <span className="font-mono text-[10px] text-cyan">P{route.priority}</span>
                <span className={`font-mono text-[10px] ${route.available ? 'text-ok' : 'text-text-tertiary'}`}>
                  {route.status || (route.available ? 'healthy' : 'unavailable')}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-tertiary">—</p>
        )}
      </section>

      {/* Governance Policies */}
      <section>
        <h3 className="wv-label mb-3">Governance Policies</h3>
        {governance?.policies ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 wv-label font-normal">Risk Class</th>
                  <th className="text-left py-2 wv-label font-normal">Level</th>
                  <th className="text-left py-2 wv-label font-normal">Authority</th>
                  <th className="text-left py-2 wv-label font-normal">Human</th>
                  <th className="text-left py-2 wv-label font-normal">Blocking</th>
                </tr>
              </thead>
              <tbody>
                {governance.policies.map((p) => (
                  <tr key={p.risk_class} className="border-b border-border">
                    <td className="py-2 font-mono text-xs">{p.risk_class}</td>
                    <td className="py-2">
                      <span className={`font-mono text-xs px-2 py-1 rounded uppercase ${
                        p.risk_level === 'CRITICAL' ? 'text-danger bg-danger/10'
                          : p.risk_level === 'HIGH' ? 'text-warn bg-warn/10'
                          : 'text-text-secondary bg-surface-overlay'
                      }`}>
                        {p.risk_level}
                      </span>
                    </td>
                    <td className="py-2">
                      <span className={`font-mono text-xs ${AUTHORITY_COLORS[p.authority] || 'text-text-secondary'}`}>
                        {p.authority}
                      </span>
                    </td>
                    <td className="py-2">
                      <span className={`w-2 h-2 rounded-full inline-block ${p.requires_human ? 'bg-warn' : 'bg-ok'}`} />
                    </td>
                    <td className="py-2">
                      <span className={`w-2 h-2 rounded-full inline-block ${p.is_blocking_class ? 'bg-danger' : 'bg-text-tertiary'}`} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-text-tertiary">Loading governance data...</p>
        )}

        {governance?.safe_roots && governance?.allowed_shell_prefixes && (
          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="wv-card px-3 py-2">
              <p className="wv-label mb-1">Safe Roots</p>
              <div className="space-y-1">
                {governance.safe_roots.map((r) => (
                  <p key={r} className="text-xs font-mono text-ok">{r}</p>
                ))}
              </div>
            </div>
            <div className="wv-card px-3 py-2">
              <p className="wv-label mb-1">Shell Prefixes</p>
              <div className="space-y-1">
                {governance.allowed_shell_prefixes.map((p) => (
                  <p key={p} className="text-xs font-mono text-cyan">{p}</p>
                ))}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Device Management */}
      <DeviceManagementSection />

    </div>
  )
}

const ROLE_BADGE: Record<string, string> = {
  orchestrator: 'text-cyan',
  executor: 'text-ok',
  controller: 'text-text-secondary',
}

function DeviceManagementSection() {
  const devices = useDeviceStore((s) => s.devices)
  const scanResult = useDeviceStore((s) => s.scanResult)
  const scanning = useDeviceStore((s) => s.scanning)
  const provisioning = useDeviceStore((s) => s.provisioning)
  const fetchDevices = useDeviceStore((s) => s.fetchDevices)
  const scanPeers = useDeviceStore((s) => s.scanPeers)
  const removeDevice = useDeviceStore((s) => s.removeDevice)
  const provisionDevice = useDeviceStore((s) => s.provisionDevice)
  const inviteDevice = useDeviceStore((s) => s.inviteDevice)

  const [inviteKey, setInviteKey] = useState<string | null>(null)
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null)

  usePolling(fetchDevices, 30000)

  const handleInvite = async () => {
    const key = await inviteDevice({ preauthorized: true, expiry_seconds: 3600 })
    setInviteKey(key)
  }

  const handleRemove = async (id: string) => {
    if (confirmRemove !== id) {
      setConfirmRemove(id)
      return
    }
    await removeDevice(id)
    setConfirmRemove(null)
  }

  return (
    <section>
      <div className="flex items-center gap-3 mb-3">
        <h3 className="wv-label">Device Management</h3>
        <button onClick={handleInvite} className="px-2 py-1 text-[10px] font-mono rounded bg-cyan-glow text-cyan border border-cyan/20">
          invite
        </button>
        <button onClick={scanPeers} className="px-2 py-1 text-[10px] font-mono rounded bg-surface-overlay text-text-secondary border border-border" disabled={scanning}>
          {scanning ? 'scanning...' : 'scan'}
        </button>
      </div>

      {inviteKey && (
        <div className="wv-card px-3 py-2 mb-3">
          <p className="wv-label mb-1">Tailscale Auth Key (1h expiry)</p>
          <code className="text-xs font-mono text-ok break-all select-all">{inviteKey}</code>
          <p className="text-[10px] text-text-tertiary mt-1">
            Run on the new device: <code className="text-cyan">tailscale up --auth-key={inviteKey}</code>
          </p>
          <button onClick={() => setInviteKey(null)} className="text-[10px] text-text-tertiary mt-1 underline">dismiss</button>
        </div>
      )}

      {/* Registered devices */}
      <div className="space-y-1.5 mb-4">
        {devices.map((d) => (
          <div key={d.id} className="wv-card flex items-center gap-3 px-3 py-2">
            <span className={`w-2 h-2 rounded-full shrink-0 ${d.online ? 'bg-ok' : 'bg-text-tertiary'}`} />
            <span className="text-sm flex-1">{d.display_name}</span>
            <span className="font-mono text-[10px] text-text-tertiary">{d.os}</span>
            <span className={`font-mono text-[10px] ${ROLE_BADGE[d.role] ?? 'text-text-tertiary'}`}>{d.role}</span>
            {d.compute && <span className="wv-badge wv-badge-ok text-[9px]">compute</span>}
            {d.role !== 'orchestrator' && !d.always_online && (
              <>
                {d.compute && (
                  <button
                    onClick={() => provisionDevice(d.id)}
                    className="text-[10px] text-cyan underline"
                    disabled={provisioning === d.id}
                  >
                    {provisioning === d.id ? 'provisioning...' : 're-provision'}
                  </button>
                )}
                <button
                  onClick={() => handleRemove(d.id)}
                  className={`text-[10px] ${confirmRemove === d.id ? 'text-danger font-semibold' : 'text-text-tertiary'} underline`}
                >
                  {confirmRemove === d.id ? 'confirm remove?' : 'remove'}
                </button>
              </>
            )}
          </div>
        ))}
      </div>

      {/* Scan results — unregistered peers with diagnosis + onboarding actions */}
      {scanResult && scanResult.unregistered > 0 && (
        <div>
          <p className="wv-label mb-2">Unregistered Peers ({scanResult.unregistered})</p>
          <div className="space-y-1.5">
            {scanResult.peers.map((p: TailscalePeer) => (
              <DeviceDiagnosisInline
                key={p.dns_name || p.hostname}
                peer={p}
                onRegistered={fetchDevices}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
