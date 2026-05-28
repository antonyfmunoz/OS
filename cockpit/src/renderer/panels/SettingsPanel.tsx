import { useSettingsStore } from '../stores/settingsStore'
import { usePolling } from '../hooks/usePolling'

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
                <span className={`w-2 h-2 rounded-full shrink-0 ${route.enabled ? 'bg-ok' : 'bg-text-tertiary'}`} />
                <span className="text-sm flex-1">{route.provider}</span>
                <span className="font-mono text-xs text-cyan">P{route.priority}</span>
                <span className={`font-mono text-xs ${route.enabled ? 'text-ok' : 'text-text-tertiary'}`}>
                  {route.enabled ? 'ACTIVE' : 'DISABLED'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-tertiary">Loading...</p>
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
                      <span className={`font-mono text-xs px-1.5 py-0.5 rounded uppercase ${
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
              <div className="space-y-0.5">
                {governance.safe_roots.map((r) => (
                  <p key={r} className="text-xs font-mono text-ok">{r}</p>
                ))}
              </div>
            </div>
            <div className="wv-card px-3 py-2">
              <p className="wv-label mb-1">Shell Prefixes</p>
              <div className="space-y-0.5">
                {governance.allowed_shell_prefixes.map((p) => (
                  <p key={p} className="text-xs font-mono text-cyan">{p}</p>
                ))}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Notification Settings */}
      <section>
        <h3 className="wv-label mb-3">Notifications</h3>
        {settings ? (
          <div className="flex gap-4">
            {Object.entries(settings.notifications).map(([key, enabled]) => (
              <div key={key} className="wv-card flex items-center gap-2 px-3 py-2">
                <span className={`w-2 h-2 rounded-full ${enabled ? 'bg-ok' : 'bg-text-tertiary'}`} />
                <span className="text-sm capitalize">{key}</span>
                <span className={`font-mono text-xs ${enabled ? 'text-ok' : 'text-text-tertiary'}`}>
                  {enabled ? 'ON' : 'OFF'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-tertiary">Loading...</p>
        )}
      </section>
    </div>
  )
}
