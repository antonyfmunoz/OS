import { useState, useEffect, useCallback } from 'react'

const API_BASE = '/api/umh'

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface-raised border border-border-subtle rounded px-3 py-2">
      <div className="text-xs text-text-tertiary">{label}</div>
      <div className="text-sm font-medium text-text-primary truncate">{value}</div>
    </div>
  )
}

function formatTimestamp(ts: number): string {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString()
}

function getProfileBadgeColor(profile: string): string {
  const colors: Record<string, string> = {
    engineer: 'bg-blue-500/20 text-blue-400',
    founder: 'bg-purple-500/20 text-purple-400',
    artist: 'bg-pink-500/20 text-pink-400',
    content: 'bg-green-500/20 text-green-400',
    research: 'bg-yellow-500/20 text-yellow-400',
    admin: 'bg-orange-500/20 text-orange-400',
  }
  return colors[profile] || 'bg-gray-500/20 text-gray-400'
}

function getModeBadgeColor(mode: string): string {
  const colors: Record<string, string> = {
    day: 'bg-amber-500/20 text-amber-400',
    night: 'bg-indigo-500/20 text-indigo-400',
    afk: 'bg-gray-500/20 text-gray-400',
    maintenance: 'bg-orange-500/20 text-orange-400',
    security: 'bg-red-500/20 text-red-400',
    focus: 'bg-cyan-500/20 text-cyan-400',
    emergency: 'bg-red-600/20 text-red-300',
  }
  return colors[mode] || 'bg-gray-500/20 text-gray-400'
}

type Tab = 'active' | 'profiles' | 'modes' | 'transitions' | 'conflicts' | 'preferences'

export function ProfilePanel() {
  const [tab, setTab] = useState<Tab>('active')
  const [state, setState] = useState<any>(null)
  const [profiles, setProfiles] = useState<any[]>([])
  const [systemModes, setSystemModes] = useState<any[]>([])
  const [timeline, setTimeline] = useState<any[]>([])
  const [conflicts, setConflicts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const [stateRes, profilesRes, modesRes, timelineRes, conflictsRes] = await Promise.all([
        fetch(`${API_BASE}/profile/state`).then(r => r.json()),
        fetch(`${API_BASE}/profile/profiles`).then(r => r.json()),
        fetch(`${API_BASE}/profile/system-modes`).then(r => r.json()),
        fetch(`${API_BASE}/profile/timeline?limit=30`).then(r => r.json()),
        fetch(`${API_BASE}/profile/conflicts`).then(r => r.json()),
      ])
      if (stateRes.success) setState(stateRes.state)
      if (profilesRes.success) setProfiles(profilesRes.profiles || [])
      if (modesRes.success) setSystemModes(modesRes.system_modes || [])
      if (timelineRes.success) setTimeline(timelineRes.events || [])
      if (conflictsRes.success) setConflicts(conflictsRes.conflicts || [])
    } catch (e) {
      console.error('Profile data fetch failed:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const iv = setInterval(fetchData, 15000)
    return () => clearInterval(iv)
  }, [fetchData])

  const activateProfile = async (name: string) => {
    await fetch(`${API_BASE}/profile/activate-profile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_mode: name, source: 'cockpit' }),
    })
    fetchData()
  }

  const deactivateProfile = async () => {
    await fetch(`${API_BASE}/profile/deactivate-profile`, { method: 'POST' })
    fetchData()
  }

  const activateSystemMode = async (name: string) => {
    await fetch(`${API_BASE}/profile/activate-system-mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode_name: name, source: 'cockpit' }),
    })
    fetchData()
  }

  const deactivateSystemMode = async (name: string) => {
    await fetch(`${API_BASE}/profile/deactivate-system-mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode_name: name }),
    })
    fetchData()
  }

  const activeProfile = state?.profile_state?.state?.active_profile_mode || ''
  const activeModes = state?.system_modes?.active_modes || []
  const ctx = state?.context || {}

  const tabs: { key: Tab; label: string }[] = [
    { key: 'active', label: 'Active' },
    { key: 'profiles', label: 'Profiles' },
    { key: 'modes', label: 'System Modes' },
    { key: 'transitions', label: 'Transitions' },
    { key: 'conflicts', label: 'Conflicts' },
    { key: 'preferences', label: 'Preferences' },
  ]

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4">
      <div className="flex items-center mb-4">
        <h2 className="text-lg font-semibold text-text-primary">Profile Runtime</h2>
        <span className="ml-2 text-xs text-text-tertiary">work identity & system modes</span>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        <KpiCard label="Profile" value={activeProfile || 'None'} />
        <KpiCard label="System Modes" value={`${activeModes.length} active`} />
        <KpiCard label="Conflicts" value={`${conflicts.length}`} />
        <KpiCard label="Interruption" value={ctx.interruption_preference || '—'} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-border-subtle pb-2">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-1.5 text-xs rounded-t transition-colors ${
              tab === t.key
                ? 'bg-surface-raised text-text-primary border border-border-subtle border-b-0'
                : 'text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t.label}
            {t.key === 'conflicts' && conflicts.length > 0 && (
              <span className="ml-1 bg-red-500/20 text-red-400 px-1 rounded text-[10px]">
                {conflicts.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {loading && <p className="text-xs text-text-tertiary">—</p>}

      {/* Active Tab */}
      {tab === 'active' && state && (
        <div className="space-y-4">
          <div className="bg-surface-raised border border-border-subtle rounded p-3">
            <h3 className="text-sm font-medium text-text-primary mb-2">Active Profile</h3>
            {activeProfile ? (
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getProfileBadgeColor(activeProfile)}`}>
                  {activeProfile.toUpperCase()}
                </span>
                <span className="text-xs text-text-tertiary">
                  via {state.profile_state?.state?.activation_source || '—'}
                </span>
                {state.profile_state?.state?.manual_override && (
                  <span className="text-[10px] text-amber-400 bg-amber-500/10 px-1 rounded">OVERRIDE</span>
                )}
                <button
                  onClick={deactivateProfile}
                  className="ml-auto text-xs text-text-tertiary hover:text-red-400 transition-colors"
                >
                  Deactivate
                </button>
              </div>
            ) : (
              <p className="text-xs text-text-tertiary">No profile active</p>
            )}
          </div>

          <div className="bg-surface-raised border border-border-subtle rounded p-3">
            <h3 className="text-sm font-medium text-text-primary mb-2">Active System Modes</h3>
            {activeModes.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {activeModes.map((m: string) => (
                  <div key={m} className="flex items-center gap-1">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${getModeBadgeColor(m)}`}>
                      {m.toUpperCase()}
                    </span>
                    <button
                      onClick={() => deactivateSystemMode(m)}
                      className="text-[10px] text-text-tertiary hover:text-red-400"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-tertiary">No system modes active</p>
            )}
          </div>

          {ctx.workspace_template && (
            <div className="bg-surface-raised border border-border-subtle rounded p-3">
              <h3 className="text-sm font-medium text-text-primary mb-2">Context</h3>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-text-tertiary">Workspace Template:</span>{' '}
                  <span className="text-text-secondary">{ctx.workspace_template}</span>
                </div>
                <div>
                  <span className="text-text-tertiary">Risk Tolerance:</span>{' '}
                  <span className="text-text-secondary">{ctx.risk_tolerance}</span>
                </div>
                <div>
                  <span className="text-text-tertiary">Notification Policy:</span>{' '}
                  <span className="text-text-secondary">{ctx.effective_notification_policy}</span>
                </div>
                <div>
                  <span className="text-text-tertiary">Attention:</span>{' '}
                  <span className="text-text-secondary">{ctx.attention_state}</span>
                </div>
              </div>
              {ctx.preferred_domains?.length > 0 && (
                <div className="mt-2">
                  <span className="text-xs text-text-tertiary">Preferred Domains:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {ctx.preferred_domains.map((d: string) => (
                      <span key={d} className="text-[10px] bg-surface px-1.5 py-0.5 rounded text-text-secondary">
                        {d}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {state.latest_plan?.plan_id && (
            <div className="bg-surface-raised border border-border-subtle rounded p-3">
              <h3 className="text-sm font-medium text-text-primary mb-2">Latest Activation Plan</h3>
              <div className="text-xs space-y-1">
                <div>
                  <span className="text-text-tertiary">Target:</span>{' '}
                  <span className="text-text-secondary">{state.latest_plan.target_profile}</span>
                </div>
                <div>
                  <span className="text-text-tertiary">Template:</span>{' '}
                  <span className="text-text-secondary">{state.latest_plan.workspace_template_suggestion}</span>
                </div>
                <div>
                  <span className="text-text-tertiary">Status:</span>{' '}
                  <span className="text-amber-400">{state.latest_plan.status}</span>
                </div>
                {state.latest_plan.cockpit_panel_preference?.length > 0 && (
                  <div>
                    <span className="text-text-tertiary">Panels:</span>{' '}
                    <span className="text-text-secondary">
                      {state.latest_plan.cockpit_panel_preference.join(', ')}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Profiles Tab */}
      {tab === 'profiles' && (
        <div className="space-y-2">
          {profiles.map((p: any) => (
            <div key={p.name} className="bg-surface-raised border border-border-subtle rounded p-3">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getProfileBadgeColor(p.name)}`}>
                    {p.name.toUpperCase()}
                  </span>
                  {p.name === activeProfile && (
                    <span className="text-[10px] text-green-400 bg-green-500/10 px-1 rounded">ACTIVE</span>
                  )}
                </div>
                {p.name !== activeProfile && (
                  <button
                    onClick={() => activateProfile(p.name)}
                    className="text-xs text-text-tertiary hover:text-text-primary transition-colors"
                  >
                    Activate
                  </button>
                )}
              </div>
              <p className="text-xs text-text-tertiary mb-2">{p.description}</p>
              <div className="grid grid-cols-2 gap-1 text-[10px]">
                <div>
                  <span className="text-text-tertiary">Template:</span>{' '}
                  <span className="text-text-secondary">{p.default_workspace_template}</span>
                </div>
                <div>
                  <span className="text-text-tertiary">Interruption:</span>{' '}
                  <span className="text-text-secondary">{p.interruption_preference}</span>
                </div>
                <div>
                  <span className="text-text-tertiary">Risk:</span>{' '}
                  <span className="text-text-secondary">{p.risk_tolerance}</span>
                </div>
                <div>
                  <span className="text-text-tertiary">Domains:</span>{' '}
                  <span className="text-text-secondary">{p.preferred_domains?.join(', ')}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* System Modes Tab */}
      {tab === 'modes' && (
        <div className="space-y-2">
          {systemModes.map((m: any) => (
            <div key={m.name} className="bg-surface-raised border border-border-subtle rounded p-3">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getModeBadgeColor(m.name)}`}>
                    {m.name.toUpperCase()}
                  </span>
                  {activeModes.includes(m.name) && (
                    <span className="text-[10px] text-green-400 bg-green-500/10 px-1 rounded">ACTIVE</span>
                  )}
                  {m.exclusivity_group && (
                    <span className="text-[10px] text-text-tertiary">
                      group: {m.exclusivity_group}
                    </span>
                  )}
                </div>
                {activeModes.includes(m.name) ? (
                  <button
                    onClick={() => deactivateSystemMode(m.name)}
                    className="text-xs text-red-400 hover:text-red-300 transition-colors"
                  >
                    Deactivate
                  </button>
                ) : (
                  <button
                    onClick={() => activateSystemMode(m.name)}
                    className="text-xs text-text-tertiary hover:text-text-primary transition-colors"
                  >
                    Activate
                  </button>
                )}
              </div>
              <p className="text-xs text-text-tertiary mb-1">{m.description}</p>
              <div className="text-[10px] text-text-tertiary">
                Priority: {m.priority} | Effects: {Object.keys(m.effects || {}).join(', ') || 'none'}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Transitions Tab */}
      {tab === 'transitions' && (
        <div className="space-y-1">
          {timeline.length === 0 && (
            <p className="text-xs text-text-tertiary">No transitions recorded</p>
          )}
          {[...timeline].reverse().map((e: any, i: number) => (
            <div key={i} className="bg-surface-raised border border-border-subtle rounded px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-secondary">{e.summary}</span>
                <span className="text-[10px] text-text-tertiary">{formatTimestamp(e.timestamp)}</span>
              </div>
              <span className="text-[10px] text-text-tertiary">{e.event_type}</span>
            </div>
          ))}
        </div>
      )}

      {/* Conflicts Tab */}
      {tab === 'conflicts' && (
        <div className="space-y-2">
          {conflicts.length === 0 && (
            <div className="bg-green-500/10 border border-green-500/20 rounded p-3">
              <p className="text-xs text-green-400">No conflicts detected</p>
            </div>
          )}
          {conflicts.map((c: any, i: number) => (
            <div key={i} className={`border rounded p-3 ${
              c.severity === 'error' ? 'bg-red-500/10 border-red-500/20' :
              c.severity === 'critical' ? 'bg-red-600/10 border-red-600/20' :
              'bg-amber-500/10 border-amber-500/20'
            }`}>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-[10px] px-1 rounded font-medium ${
                  c.severity === 'error' ? 'bg-red-500/20 text-red-400' :
                  c.severity === 'critical' ? 'bg-red-600/20 text-red-300' :
                  'bg-amber-500/20 text-amber-400'
                }`}>
                  {c.severity?.toUpperCase()}
                </span>
                <span className="text-xs text-text-secondary">{c.conflict_type}</span>
              </div>
              <p className="text-xs text-text-secondary">{c.description}</p>
              <div className="flex gap-1 mt-1">
                {c.involved_modes?.map((m: string) => (
                  <span key={m} className="text-[10px] bg-surface px-1 rounded text-text-tertiary">{m}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Preferences Tab */}
      {tab === 'preferences' && (
        <div className="space-y-3">
          {activeProfile ? (
            <div className="bg-surface-raised border border-border-subtle rounded p-3">
              <h3 className="text-sm font-medium text-text-primary mb-2">
                Active Profile: {activeProfile.toUpperCase()}
              </h3>
              {ctx.domain_weights && Object.keys(ctx.domain_weights).length > 0 && (
                <div>
                  <span className="text-xs text-text-tertiary">Domain Weights:</span>
                  <div className="mt-1 space-y-1">
                    {Object.entries(ctx.domain_weights as Record<string, number>)
                      .sort(([, a], [, b]) => b - a)
                      .map(([domain, weight]) => (
                        <div key={domain} className="flex items-center gap-2 text-xs">
                          <span className="text-text-secondary w-24">{domain}</span>
                          <div className="flex-1 bg-surface rounded-full h-1.5">
                            <div
                              className="bg-accent-primary rounded-full h-1.5 transition-all"
                              style={{ width: `${(weight as number) * 100}%` }}
                            />
                          </div>
                          <span className="text-text-tertiary w-8 text-right">{weight}</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-text-tertiary">Activate a profile to see preferences</p>
          )}
        </div>
      )}
    </div>
  )
}
