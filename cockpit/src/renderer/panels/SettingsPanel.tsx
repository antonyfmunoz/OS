import { useState, useEffect, useCallback } from 'react'
import { useSettingsStore } from '../stores/settingsStore'
import { useDeviceStore } from '../stores/deviceStore'
import type { TailscalePeer } from '../stores/deviceStore'
import { usePolling } from '../hooks/usePolling'
import { DeviceDiagnosisInline } from '../components/DeviceDiagnosisInline'
import { isPushSupported, subscribeToPush, unsubscribeFromPush, isSubscribed, getPushState } from '../lib/pushNotifications'
import { fetchApi } from '../api/client'

const AUTHORITY_COLORS: Record<string, string> = {
  AUTONOMOUS: 'text-ok',
  NOTIFY: 'text-cyan',
  APPROVE: 'text-warn',
  ESCALATE: 'text-warn',
  DENY: 'text-danger',
}

const AUTHORITY_LEVELS = ['AUTONOMOUS', 'NOTIFY', 'APPROVE', 'ESCALATE', 'DENY']

const GOVERNANCE_BLOCKED: Record<string, Set<string>> = {
  FINANCIAL: new Set(['AUTONOMOUS']),
  SECURITY_SENSITIVE: new Set(['AUTONOMOUS']),
}

const ALL_ROLES = ['controller', 'executor', 'orchestrator']

export function SettingsPanel() {
  const settings = useSettingsStore((s) => s.settings)
  const settingsError = useSettingsStore((s) => s.settingsError)
  const governance = useSettingsStore((s) => s.governance)
  const governanceError = useSettingsStore((s) => s.governanceError)
  const fetchSettings = useSettingsStore((s) => s.fetchSettings)
  const fetchGovernance = useSettingsStore((s) => s.fetchGovernance)

  usePolling(() => {
    fetchSettings()
    fetchGovernance()
  }, 30000)

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      <h2 className="text-lg font-semibold">System Configuration</h2>
      <ModelRoutingSection />
      <GovernanceSection />
      <DeviceManagementSection />
      <NotificationsSection />
    </div>
  )
}

// ── Model Routing ───────────────────────────────────────────────────

type RoutingTab = 'all' | 'purpose' | 'role'

function ModelRoutingSection() {
  const settings = useSettingsStore((s) => s.settings)
  const settingsError = useSettingsStore((s) => s.settingsError)
  const toggleProvider = useSettingsStore((s) => s.toggleProvider)
  const setRoleSlot = useSettingsStore((s) => s.setRoleSlot)
  const [tab, setTab] = useState<RoutingTab>('all')
  const [warning, setWarning] = useState<string | null>(null)

  return (
    <section>
      <h3 className="wv-label mb-3">Model Routing</h3>
      {settingsError && !settings?.model_routing && (
        <p className="text-xs text-danger py-2">{settingsError}</p>
      )}
      {settings?.model_routing ? (
        <>
          <div className="flex gap-1 mb-3">
            {(['all', 'purpose', 'role'] as RoutingTab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-2 py-1 text-[10px] font-mono rounded border ${
                  tab === t
                    ? 'bg-cyan-glow text-cyan border-cyan/20'
                    : 'bg-surface-overlay text-text-secondary border-border'
                }`}
              >
                {t === 'all' ? 'All' : t === 'purpose' ? 'By Purpose' : 'By Role'}
              </button>
            ))}
          </div>

          {warning && (
            <p className="text-xs text-warn py-1 mb-2">{warning}</p>
          )}

          {tab === 'all' && (
            <div className="space-y-1.5">
              {settings.model_routing.map((route) => (
                <div key={route.provider} className="wv-card flex items-center gap-3 px-3 py-2">
                  <button
                    onClick={async () => {
                      const resp = await toggleProvider(route.provider, !route.available)
                      if (resp?.warnings?.length) setWarning(resp.warnings.join('; '))
                      else setWarning(null)
                    }}
                    className={`w-2 h-2 rounded-full shrink-0 cursor-pointer ${route.available ? 'bg-ok' : 'bg-text-tertiary'}`}
                    title={route.available ? 'Click to disable' : 'Click to enable'}
                  />
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
          )}

          {tab === 'purpose' && settings.purpose_routing && (
            <div className="space-y-1.5">
              {Object.entries(settings.purpose_routing).map(([purpose, roles]) => (
                <details key={purpose} className="wv-card px-3 py-2">
                  <summary className="cursor-pointer text-sm">
                    <span className="font-mono text-cyan">{purpose}</span>
                    <span className="text-[10px] text-text-tertiary ml-2">
                      {roles.join(' → ')}
                    </span>
                  </summary>
                  <div className="mt-2 space-y-1 pl-4">
                    {roles.map((role, i) => {
                      const providerKey = settings.role_slots?.[role]
                      return (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <span className="text-text-tertiary">{i + 1}.</span>
                          <span className="font-mono text-warn">{role}</span>
                          <span className="text-text-tertiary">→</span>
                          <span className="font-mono text-ok">{providerKey || '?'}</span>
                        </div>
                      )
                    })}
                  </div>
                </details>
              ))}
            </div>
          )}

          {tab === 'role' && settings.role_slots && (
            <div className="space-y-1.5">
              {Object.entries(settings.role_slots).map(([role, providerKey]) => (
                <div key={role} className="wv-card px-3 py-2">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm text-warn flex-1">{role}</span>
                    <select
                      value={providerKey}
                      onChange={async (e) => {
                        const resp = await setRoleSlot(role, e.target.value)
                        if (resp?.warnings?.length) setWarning(resp.warnings.join('; '))
                        else setWarning(null)
                      }}
                      className="bg-surface-overlay text-text-primary text-xs font-mono px-2 py-1 rounded border border-border"
                    >
                      {settings.provider_keys?.map((k) => (
                        <option key={k} value={k}>{k}</option>
                      ))}
                    </select>
                  </div>
                  {settings.role_failover?.[role] && (
                    <p className="text-[10px] text-text-tertiary mt-1">
                      failover: {settings.role_failover[role]}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      ) : !settingsError ? (
        <p className="text-xs text-text-tertiary">Loading...</p>
      ) : null}
    </section>
  )
}

// ── Governance ──────────────────────────────────────────────────────

function GovernanceSection() {
  const governance = useSettingsStore((s) => s.governance)
  const governanceError = useSettingsStore((s) => s.governanceError)
  const patchGovernance = useSettingsStore((s) => s.patchGovernance)
  const [govWarning, setGovWarning] = useState<string | null>(null)

  const handleAuthorityChange = async (riskClass: string, newAuth: string) => {
    const resp = await patchGovernance({ [riskClass]: newAuth })
    if (resp?.warnings?.length) {
      setGovWarning(resp.warnings.join('; '))
      setTimeout(() => setGovWarning(null), 5000)
    } else if (resp?.errors?.length) {
      setGovWarning(resp.errors.join('; '))
      setTimeout(() => setGovWarning(null), 5000)
    } else {
      setGovWarning(null)
    }
  }

  return (
    <section>
      <h3 className="wv-label mb-3">Governance Policies</h3>
      {governanceError && !governance?.policies && (
        <p className="text-xs text-danger py-2">{governanceError}</p>
      )}
      {govWarning && (
        <p className="text-xs text-warn py-1 mb-2">{govWarning}</p>
      )}
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
              {governance.policies.map((p) => {
                const blocked = GOVERNANCE_BLOCKED[p.risk_class] ?? new Set()
                return (
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
                      <select
                        value={p.authority}
                        onChange={(e) => handleAuthorityChange(p.risk_class, e.target.value)}
                        className={`font-mono text-xs px-2 py-1 rounded border border-border bg-surface-overlay ${
                          AUTHORITY_COLORS[p.authority] || 'text-text-secondary'
                        }`}
                      >
                        {AUTHORITY_LEVELS.map((lvl) => (
                          <option key={lvl} value={lvl} disabled={blocked.has(lvl)}>
                            {lvl}{blocked.has(lvl) ? ' (blocked)' : ''}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2">
                      <span className={`w-2 h-2 rounded-full inline-block ${p.requires_human ? 'bg-warn' : 'bg-ok'}`} />
                    </td>
                    <td className="py-2">
                      <span className={`w-2 h-2 rounded-full inline-block ${p.is_blocking_class ? 'bg-danger' : 'bg-text-tertiary'}`} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : !governanceError ? (
        <p className="text-xs text-text-tertiary">Loading governance data...</p>
      ) : null}

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
  )
}

// ── Device Management ───────────────────────────────────────────────

const ROLE_BADGE: Record<string, string> = {
  orchestrator: 'text-cyan',
  executor: 'text-ok',
  controller: 'text-text-secondary',
}

const ROLE_STATUS_DOT: Record<string, string> = {
  confirmed: 'bg-ok',
  provisional: 'bg-warn',
  needs_review: 'bg-orange-400',
  rejected: 'bg-danger',
}

const ROLE_STATUS_LABEL: Record<string, string> = {
  confirmed: 'Confirmed',
  provisional: 'Provisional',
  needs_review: 'Needs Review',
  rejected: 'Rejected',
}

const ROLE_SOURCE_LABEL: Record<string, string> = {
  operator: 'Set by operator',
  diagnosis: 'From diagnosis',
  heuristic: 'Heuristic',
  daemon_report: 'Daemon report',
}

const ROLE_CONFIRM_TEXT: Record<string, string> = {
  executor: 'This grants compute execution authority. Confirm?',
  orchestrator: 'This grants orchestration authority. Only one orchestrator should be active. Confirm?',
}

function DeviceManagementSection() {
  const devices = useDeviceStore((s) => s.devices)
  const devicesLoaded = useDeviceStore((s) => s.devicesLoaded)
  const devicesError = useDeviceStore((s) => s.devicesError)
  const scanResult = useDeviceStore((s) => s.scanResult)
  const scanning = useDeviceStore((s) => s.scanning)
  const provisioning = useDeviceStore((s) => s.provisioning)
  const fetchDevices = useDeviceStore((s) => s.fetchDevices)
  const scanPeers = useDeviceStore((s) => s.scanPeers)
  const removeDevice = useDeviceStore((s) => s.removeDevice)
  const provisionDevice = useDeviceStore((s) => s.provisionDevice)
  const inviteDevice = useDeviceStore((s) => s.inviteDevice)
  const updateDevice = useDeviceStore((s) => s.updateDevice)

  const [inviteKey, setInviteKey] = useState<string | null>(null)
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null)
  const [confirmRole, setConfirmRole] = useState<{ id: string; role: string } | null>(null)
  const [deviceWarning, setDeviceWarning] = useState<string | null>(null)

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

  const handleRoleChange = async (id: string, newRole: string) => {
    if (newRole === 'executor' || newRole === 'orchestrator') {
      setConfirmRole({ id, role: newRole })
      return
    }
    const resp = await updateDevice(id, { role: newRole })
    if (resp.warnings?.length) {
      setDeviceWarning(resp.warnings.join('; '))
      setTimeout(() => setDeviceWarning(null), 5000)
    }
  }

  const confirmRoleChange = async () => {
    if (!confirmRole) return
    const resp = await updateDevice(confirmRole.id, { role: confirmRole.role })
    if (resp.warnings?.length) {
      setDeviceWarning(resp.warnings.join('; '))
      setTimeout(() => setDeviceWarning(null), 5000)
    }
    setConfirmRole(null)
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

      {confirmRole && (
        <div className="wv-card px-3 py-2 mb-3 border border-warn/30">
          <p className="text-xs text-warn mb-2">{ROLE_CONFIRM_TEXT[confirmRole.role]}</p>
          <div className="flex gap-2">
            <button onClick={confirmRoleChange} className="px-2 py-1 text-[10px] font-mono rounded bg-warn/20 text-warn border border-warn/30">
              confirm
            </button>
            <button onClick={() => setConfirmRole(null)} className="px-2 py-1 text-[10px] font-mono rounded bg-surface-overlay text-text-secondary border border-border">
              cancel
            </button>
          </div>
        </div>
      )}

      {deviceWarning && (
        <p className="text-xs text-warn py-1 mb-2">{deviceWarning}</p>
      )}

      {!devicesLoaded && devices.length === 0 && (
        <p className="text-xs text-text-tertiary py-2">Loading devices...</p>
      )}
      {devicesError && devices.length === 0 && (
        <p className="text-xs text-danger py-2">{devicesError}</p>
      )}
      <div className="space-y-1.5 mb-4">
        {devices.map((d) => {
          const allowed = d.allowed_roles ?? ALL_ROLES
          const statusDot = ROLE_STATUS_DOT[d.role_status ?? ''] ?? 'bg-text-tertiary'
          const statusLabel = ROLE_STATUS_LABEL[d.role_status ?? ''] ?? ''
          const sourceLabel = ROLE_SOURCE_LABEL[d.role_source ?? ''] ?? ''

          return (
            <div key={d.id} className="wv-card px-3 py-2">
              <div className="flex items-center gap-3">
                <span className={`w-2 h-2 rounded-full shrink-0 ${d.online ? 'bg-ok' : 'bg-text-tertiary'}`} />
                <span className="text-sm flex-1">{d.display_name}</span>
                <span className="font-mono text-[10px] text-text-tertiary">{d.os}</span>
                <select
                  value={d.role}
                  onChange={(e) => handleRoleChange(d.id, e.target.value)}
                  className={`font-mono text-[10px] px-2 py-1 rounded border border-border bg-surface-overlay ${ROLE_BADGE[d.role] ?? 'text-text-tertiary'}`}
                >
                  {ALL_ROLES.map((r) => {
                    const isAllowed = allowed.includes(r)
                    return (
                      <option key={r} value={r} disabled={!isAllowed}>
                        {r}{!isAllowed ? ' (unavailable)' : ''}
                      </option>
                    )
                  })}
                </select>
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
              {(statusLabel || sourceLabel) && (
                <div className="flex items-center gap-2 mt-1 pl-5">
                  {statusLabel && (
                    <span className="flex items-center gap-1">
                      <span className={`w-1.5 h-1.5 rounded-full ${statusDot}`} />
                      <span className="text-[10px] text-text-tertiary">{statusLabel}</span>
                    </span>
                  )}
                  {sourceLabel && (
                    <span className="text-[10px] text-text-tertiary">· {sourceLabel}</span>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

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

// ── Notifications ───────────────────────────────────────────────────

function isIOSSafari(): boolean {
  const ua = navigator.userAgent
  return /iPad|iPhone|iPod/.test(ua) && !('standalone' in navigator && (navigator as any).standalone)
}

function isInstalledPWA(): boolean {
  return window.matchMedia('(display-mode: standalone)').matches
    || ('standalone' in navigator && (navigator as any).standalone === true)
}

function NotificationsSection() {
  const [subscribed, setSubscribed] = useState(false)
  const [permState, setPermState] = useState<string>('default')
  const [loading, setLoading] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    const state = await getPushState()
    setPermState(state)
    if (state === 'granted') {
      setSubscribed(await isSubscribed())
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const handleToggle = async () => {
    setLoading(true)
    try {
      if (subscribed) {
        await unsubscribeFromPush()
        setSubscribed(false)
      } else {
        const sub = await subscribeToPush()
        setSubscribed(sub !== null)
      }
      await refresh()
    } finally {
      setLoading(false)
    }
  }

  const handleTest = async () => {
    setTestResult(null)
    try {
      const res = await fetchApi<{ success: boolean }>('/push/test', { method: 'POST' })
      setTestResult(res.success ? 'sent' : 'failed')
    } catch {
      setTestResult('error')
    }
  }

  const iosNeedsInstall = isIOSSafari() && !isInstalledPWA()
  const supported = isPushSupported()

  return (
    <section>
      <h3 className="wv-label mb-3">Notifications</h3>
      <div className="wv-card px-3 py-2 space-y-2">
        <div className="flex items-center gap-3">
          <span className="text-sm flex-1">
            {permState === 'denied'
              ? 'Blocked by browser'
              : !supported
                ? 'Not available'
                : subscribed
                  ? 'Enabled'
                  : 'Disabled'}
          </span>
          <button
            onClick={handleToggle}
            disabled={loading || permState === 'denied' || !supported || iosNeedsInstall}
            className="relative w-10 h-5 rounded-full transition-colors shrink-0"
            style={{ backgroundColor: subscribed ? '#00E5FF' : '#333' }}
            aria-label={subscribed ? 'Disable push notifications' : 'Enable push notifications'}
          >
            <span
              className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform"
              style={{ left: subscribed ? '22px' : '2px' }}
            />
          </button>
          {subscribed && (
            <button
              onClick={handleTest}
              className="px-2 py-1 text-[10px] font-mono rounded bg-surface-overlay text-text-secondary border border-border"
            >
              test
            </button>
          )}
        </div>
        {iosNeedsInstall && (
          <p className="text-[10px] text-warn">
            Add to Home Screen to enable push notifications on iOS.
            Tap the share icon, then &quot;Add to Home Screen&quot;.
          </p>
        )}
        {!supported && !iosNeedsInstall && (
          <p className="text-[10px] text-text-tertiary">Not supported in this browser.</p>
        )}
        {permState === 'denied' && (
          <p className="text-[10px] text-danger">Permission blocked — reset in browser site settings.</p>
        )}
        {testResult && (
          <p className={`text-[10px] ${testResult === 'sent' ? 'text-ok' : 'text-danger'}`}>
            Test: {testResult}
          </p>
        )}
      </div>
    </section>
  )
}
