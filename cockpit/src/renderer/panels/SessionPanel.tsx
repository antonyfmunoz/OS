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

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    active: 'bg-green-500/20 text-green-400',
    background: 'bg-blue-500/20 text-blue-400',
    idle: 'bg-yellow-500/20 text-yellow-400',
    suspended: 'bg-orange-500/20 text-orange-400',
    disconnected: 'bg-red-500/20 text-red-400',
  }
  return colors[status] || 'bg-gray-500/20 text-gray-400'
}

function getAuthorityColor(authority: string): string {
  const colors: Record<string, string> = {
    primary: 'bg-purple-500/20 text-purple-400',
    secondary: 'bg-cyan-500/20 text-cyan-400',
    background: 'bg-gray-500/20 text-gray-400',
  }
  return colors[authority] || 'bg-gray-500/20 text-gray-400'
}

function getTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    desktop: '🖥',
    laptop: '💻',
    phone: '📱',
    tablet: '📲',
    vps: '🔧',
    server: '🖧',
    container: '📦',
    browser: '🌐',
    'remote-desktop': '🖥',
    'agent-session': '🤖',
  }
  return icons[type] || '❓'
}

type Tab = 'active' | 'timeline' | 'handoffs' | 'devices' | 'history'

export function SessionPanel() {
  const [tab, setTab] = useState<Tab>('active')
  const [state, setState] = useState<any>(null)
  const [sessions, setSessions] = useState<any[]>([])
  const [timeline, setTimeline] = useState<any[]>([])
  const [handoffs, setHandoffs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const [stateRes, listRes, timelineRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/session/state`).then(r => r.json()),
        fetch(`${API_BASE}/session/list`).then(r => r.json()),
        fetch(`${API_BASE}/session/timeline?limit=50`).then(r => r.json()),
        fetch(`${API_BASE}/session/history`).then(r => r.json()),
      ])
      if (stateRes.success) setState(stateRes)
      if (listRes.success) setSessions(listRes.sessions || [])
      if (timelineRes.success) setTimeline(timelineRes.events || [])
      if (historyRes.success) setHandoffs(historyRes.handoffs || [])
    } catch (e) {
      console.error('session refresh failed:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 15000)
    return () => clearInterval(interval)
  }, [refresh])

  const doAction = async (endpoint: string, body: Record<string, string>) => {
    try {
      await fetch(`${API_BASE}/session/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      refresh()
    } catch (e) {
      console.error(`session ${endpoint} failed:`, e)
    }
  }

  if (loading) {
    return <div className="p-6 text-text-secondary">Loading session state...</div>
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'active', label: 'Active' },
    { id: 'timeline', label: 'Timeline' },
    { id: 'handoffs', label: 'Handoffs' },
    { id: 'devices', label: 'Devices' },
    { id: 'history', label: 'History' },
  ]

  const primary = state?.primary_session
  const activeSessions = sessions.filter(
    (s: any) => ['active', 'background', 'idle'].includes(s.status)
  )

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Session Runtime</h2>
        <button
          onClick={refresh}
          className="text-xs bg-surface-raised border border-border-subtle rounded px-2 py-1 text-text-secondary hover:text-text-primary"
        >
          Refresh
        </button>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-3">
        <KpiCard
          label="Primary"
          value={primary ? `${primary.session_type} (${primary.device_id || 'unknown'})` : 'None'}
        />
        <KpiCard label="Active" value={String(state?.total_active || 0)} />
        <KpiCard label="Total" value={String(state?.total_all || 0)} />
        <KpiCard label="Handoffs" value={String(handoffs.length)} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border-subtle">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 text-sm border-b-2 transition-colors ${
              tab === t.id
                ? 'border-accent-primary text-text-primary'
                : 'border-transparent text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'active' && (
        <div className="space-y-4">
          {/* Primary Session */}
          {primary && (
            <div className="bg-surface-raised border border-purple-500/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{getTypeIcon(primary.session_type)}</span>
                  <span className="text-sm font-medium text-text-primary">
                    {primary.session_type}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded ${getAuthorityColor('primary')}`}>
                    PRIMARY
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(primary.status)}`}>
                    {primary.status}
                  </span>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => doAction('suspend', { session_id: primary.session_id })}
                    className="text-xs bg-orange-500/20 text-orange-400 rounded px-2 py-1 hover:bg-orange-500/30"
                  >
                    Suspend
                  </button>
                  <button
                    onClick={() => doAction('disconnect', { session_id: primary.session_id })}
                    className="text-xs bg-red-500/20 text-red-400 rounded px-2 py-1 hover:bg-red-500/30"
                  >
                    Disconnect
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs text-text-secondary">
                <div>Device: {primary.device_id || '—'}</div>
                <div>Profile: {primary.profile_id || '—'}</div>
                <div>Workstation: {primary.active_workstation_mode || '—'}</div>
                <div>Host: {primary.host_id || '—'}</div>
                <div>Attention: {primary.attention_state}</div>
                <div>Last seen: {formatTimestamp(primary.last_seen_at)}</div>
              </div>
              {primary.bound_work_packets?.length > 0 && (
                <div className="mt-2 text-xs text-text-tertiary">
                  Work: {primary.bound_work_packets.join(', ')}
                </div>
              )}
            </div>
          )}

          {/* Secondary & Background Sessions */}
          {activeSessions
            .filter((s: any) => s.authority !== 'primary')
            .map((s: any) => (
              <div
                key={s.session_id}
                className="bg-surface-raised border border-border-subtle rounded-lg p-3"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span>{getTypeIcon(s.session_type)}</span>
                    <span className="text-sm text-text-primary">{s.session_type}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${getAuthorityColor(s.authority)}`}>
                      {s.authority}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(s.status)}`}>
                      {s.status}
                    </span>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={() => doAction('promote', { session_id: s.session_id })}
                      className="text-xs bg-purple-500/20 text-purple-400 rounded px-2 py-1 hover:bg-purple-500/30"
                    >
                      Promote
                    </button>
                    {s.status === 'suspended' && (
                      <button
                        onClick={() => doAction('resume', { session_id: s.session_id })}
                        className="text-xs bg-green-500/20 text-green-400 rounded px-2 py-1 hover:bg-green-500/30"
                      >
                        Resume
                      </button>
                    )}
                    {s.status === 'disconnected' && (
                      <button
                        onClick={() => doAction('restore', { session_id: s.session_id })}
                        className="text-xs bg-green-500/20 text-green-400 rounded px-2 py-1 hover:bg-green-500/30"
                      >
                        Restore
                      </button>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs text-text-secondary">
                  <div>Device: {s.device_id || '—'}</div>
                  <div>Profile: {s.profile_id || '—'}</div>
                  <div>Last seen: {formatTimestamp(s.last_seen_at)}</div>
                </div>
              </div>
            ))}

          {activeSessions.length === 0 && (
            <div className="text-center text-text-tertiary text-sm py-8">
              No active sessions
            </div>
          )}
        </div>
      )}

      {tab === 'timeline' && (
        <div className="space-y-2">
          {timeline.length === 0 ? (
            <div className="text-center text-text-tertiary text-sm py-8">No events</div>
          ) : (
            timeline.map((e: any) => (
              <div
                key={e.event_id}
                className="bg-surface-raised border border-border-subtle rounded p-3 flex items-start gap-3"
              >
                <div className="text-xs text-text-tertiary whitespace-nowrap mt-0.5">
                  {formatTimestamp(e.timestamp)}
                </div>
                <div>
                  <div className="text-sm text-text-primary">{e.summary}</div>
                  <div className="text-xs text-text-tertiary">{e.event_type}</div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === 'handoffs' && (
        <div className="space-y-3">
          {handoffs.length === 0 ? (
            <div className="text-center text-text-tertiary text-sm py-8">No handoffs</div>
          ) : (
            handoffs.map((h: any) => (
              <div
                key={h.handoff_id}
                className="bg-surface-raised border border-border-subtle rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text-primary">
                      {h.source_device_id || 'unknown'} → {h.target_device_id || 'unknown'}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        h.status === 'completed'
                          ? 'bg-green-500/20 text-green-400'
                          : h.status === 'pending'
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-gray-500/20 text-gray-400'
                      }`}
                    >
                      {h.status}
                    </span>
                  </div>
                  {h.status === 'pending' && (
                    <button
                      onClick={() => doAction('handoff/complete', { handoff_id: h.handoff_id })}
                      className="text-xs bg-green-500/20 text-green-400 rounded px-2 py-1 hover:bg-green-500/30"
                    >
                      Complete
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-text-secondary">
                  <div>Created: {formatTimestamp(h.created_at)}</div>
                  <div>Completed: {formatTimestamp(h.completed_at)}</div>
                  <div>Work packets: {h.active_work_packets?.length || 0}</div>
                  <div>Has continuity: {h.continuity_snapshot ? 'Yes' : 'No'}</div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === 'devices' && (
        <div className="space-y-2">
          {sessions.length === 0 ? (
            <div className="text-center text-text-tertiary text-sm py-8">No sessions</div>
          ) : (
            (() => {
              const byDevice: Record<string, any[]> = {}
              sessions.forEach((s: any) => {
                const key = s.device_id || 'unknown'
                if (!byDevice[key]) byDevice[key] = []
                byDevice[key].push(s)
              })
              return Object.entries(byDevice).map(([deviceId, deviceSessions]) => (
                <div
                  key={deviceId}
                  className="bg-surface-raised border border-border-subtle rounded-lg p-4"
                >
                  <div className="text-sm font-medium text-text-primary mb-2">{deviceId}</div>
                  {deviceSessions.map((s: any) => (
                    <div
                      key={s.session_id}
                      className="flex items-center gap-2 text-xs text-text-secondary py-1"
                    >
                      <span>{getTypeIcon(s.session_type)}</span>
                      <span>{s.session_type}</span>
                      <span className={`px-1.5 py-0.5 rounded ${getStatusColor(s.status)}`}>
                        {s.status}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded ${getAuthorityColor(s.authority)}`}>
                        {s.authority}
                      </span>
                      <span className="text-text-tertiary ml-auto">
                        {formatTimestamp(s.last_seen_at)}
                      </span>
                    </div>
                  ))}
                </div>
              ))
            })()
          )}
        </div>
      )}

      {tab === 'history' && (
        <div className="space-y-2">
          {sessions
            .filter((s: any) => ['suspended', 'disconnected'].includes(s.status))
            .map((s: any) => (
              <div
                key={s.session_id}
                className="bg-surface-raised border border-border-subtle rounded p-3"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span>{getTypeIcon(s.session_type)}</span>
                  <span className="text-sm text-text-primary">{s.session_type}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(s.status)}`}>
                    {s.status}
                  </span>
                  <span className="text-xs text-text-tertiary ml-auto">
                    {s.device_id || '—'}
                  </span>
                </div>
                <div className="text-xs text-text-tertiary">
                  Started: {formatTimestamp(s.created_at)} | Last: {formatTimestamp(s.last_seen_at)}
                </div>
              </div>
            ))}
          {sessions.filter((s: any) => ['suspended', 'disconnected'].includes(s.status)).length === 0 && (
            <div className="text-center text-text-tertiary text-sm py-8">
              No ended or suspended sessions
            </div>
          )}
        </div>
      )}
    </div>
  )
}
