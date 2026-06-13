import { useEffect, useState } from 'react'
import { fetchApi } from '../api/client'

interface PresenceStatus {
  operator_present: boolean
  attention_state: string
  interruption_level: string
  active_session_count: number
  online_device_count: number
  active_device: string
  active_profile_mode: string
  interaction_surface: string
  last_interaction: number
  snapshot_count: number
}

interface DeviceData {
  device_id: string
  display_name: string
  device_type: string
  role: string
  online: boolean
  active: boolean
  session_count: number
}

interface SessionData {
  session_id: string
  host: string
  device_id: string
  profile_mode: string
  status: string
  started_at: number
  last_activity: number
  client_type: string
  interaction_surface: string
}

interface PresenceTimelineEvent {
  event_id: string
  event_type: string
  timestamp: number
  summary: string
  details: Record<string, unknown>
}

type Tab = 'overview' | 'devices' | 'sessions' | 'attention' | 'history'

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="border border-white/10 rounded p-3">
      <div className="text-xs text-white/40 uppercase tracking-wider">{label}</div>
      <div className="text-lg font-mono mt-1">{value}</div>
      {sub && <div className="text-xs text-white/30 mt-0.5">{sub}</div>}
    </div>
  )
}

function getAttentionColor(state: string): string {
  switch (state) {
    case 'focused': return 'text-blue-400'
    case 'available': return 'text-green-400'
    case 'away': return 'text-yellow-400'
    case 'sleeping': return 'text-purple-400'
    case 'offline': return 'text-white/30'
    default: return 'text-white/50'
  }
}

function getInterruptionBadge(level: string): string {
  switch (level) {
    case 'critical_only': return 'bg-red-500/20 text-red-400'
    case 'normal': return 'bg-green-500/20 text-green-400'
    case 'queue': return 'bg-yellow-500/20 text-yellow-400'
    case 'defer': return 'bg-white/5 text-white/30'
    default: return 'bg-white/5 text-white/30'
  }
}

function getEventColor(type: string): string {
  switch (type) {
    case 'operator_present': return 'bg-green-500/20 text-green-400'
    case 'operator_absent': return 'bg-red-500/20 text-red-400'
    case 'session_started': return 'bg-blue-500/20 text-blue-400'
    case 'session_ended': return 'bg-blue-500/10 text-blue-300'
    case 'attention_changed': return 'bg-yellow-500/20 text-yellow-400'
    case 'profile_changed': return 'bg-purple-500/20 text-purple-400'
    case 'device_changed': return 'bg-cyan-500/20 text-cyan-400'
    default: return 'bg-white/5 text-white/40'
  }
}

function formatTimestamp(ts: number): string {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleTimeString()
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${Math.round(seconds / 3600)}h`
}

export function PresencePanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const [status, setStatus] = useState<PresenceStatus | null>(null)
  const [devices, setDevices] = useState<DeviceData[]>([])
  const [sessions, setSessions] = useState<SessionData[]>([])
  const [timeline, setTimeline] = useState<PresenceTimelineEvent[]>([])
  const [loading, setLoading] = useState(false)

  const refresh = async () => {
    setLoading(true)
    try {
      const [statusRes, devRes, sesRes, tlRes] = await Promise.all([
        fetchApi<PresenceStatus & { success: boolean }>('/presence/status'),
        fetchApi<{ success: boolean; devices: DeviceData[] }>('/presence/devices'),
        fetchApi<{ success: boolean; sessions: SessionData[] }>('/presence/sessions'),
        fetchApi<{ success: boolean; events: PresenceTimelineEvent[] }>('/presence/timeline?limit=100'),
      ])
      if (statusRes.success) setStatus(statusRes)
      if (devRes.success) setDevices(devRes.devices ?? [])
      if (sesRes.success) setSessions(sesRes.sessions ?? [])
      if (tlRes.success) setTimeline(tlRes.events ?? [])
    } catch { /* no-op */ }
    setLoading(false)
  }

  useEffect(() => { refresh() }, [])

  const capture = async () => {
    setLoading(true)
    try {
      await fetchApi('/presence/capture', { method: 'POST' })
      await refresh()
    } catch { /* no-op */ }
    setLoading(false)
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'devices', label: 'Devices' },
    { key: 'sessions', label: 'Sessions' },
    { key: 'attention', label: 'Attention' },
    { key: 'history', label: 'History' },
  ]

  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Presence Runtime</h2>
        <div className="flex gap-2">
          <button
            onClick={capture}
            disabled={loading}
            className="px-3 py-1 text-xs border border-white/10 rounded hover:bg-white/5 disabled:opacity-30"
          >
            Capture
          </button>
          <button
            onClick={refresh}
            disabled={loading}
            className="px-3 py-1 text-xs border border-white/10 rounded hover:bg-white/5 disabled:opacity-30"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="flex gap-1 border-b border-white/10 pb-1">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-1 text-xs rounded-t ${tab === t.key ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/60'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && status && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard
              label="Status"
              value={status.operator_present ? 'Present' : 'Absent'}
              sub={status.active_device || undefined}
            />
            <KpiCard
              label="Attention"
              value={status.attention_state}
            />
            <KpiCard
              label="Sessions"
              value={String(status.active_session_count)}
              sub={`${status.online_device_count} devices online`}
            />
            <KpiCard
              label="Snapshots"
              value={String(status.snapshot_count)}
            />
          </div>

          <div className="border border-white/10 rounded p-3">
            <div className="text-xs text-white/40 uppercase tracking-wider mb-2">Current State</div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-white/40">Attention: </span>
                <span className={getAttentionColor(status.attention_state)}>{status.attention_state}</span>
              </div>
              <div>
                <span className="text-white/40">Interruption: </span>
                <span className={`px-1.5 py-0.5 rounded text-xs ${getInterruptionBadge(status.interruption_level)}`}>
                  {status.interruption_level}
                </span>
              </div>
              <div>
                <span className="text-white/40">Profile: </span>
                <span>{status.active_profile_mode || 'none'}</span>
              </div>
              <div>
                <span className="text-white/40">Surface: </span>
                <span>{status.interaction_surface || 'none'}</span>
              </div>
              <div>
                <span className="text-white/40">Device: </span>
                <span>{status.active_device || 'none'}</span>
              </div>
              <div>
                <span className="text-white/40">Last Activity: </span>
                <span>{status.last_interaction ? formatTimestamp(status.last_interaction) : 'never'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'devices' && (
        <div className="space-y-2">
          {devices.length === 0 && <div className="text-white/30 text-sm">No devices registered</div>}
          {devices.map(d => (
            <div key={d.device_id} className="border border-white/10 rounded p-3 flex items-center justify-between">
              <div>
                <div className="text-sm font-mono">{d.display_name}</div>
                <div className="text-xs text-white/40">{d.device_type} / {d.role}</div>
              </div>
              <div className="flex items-center gap-2">
                {d.session_count > 0 && (
                  <span className="text-xs text-white/40">{d.session_count} session{d.session_count > 1 ? 's' : ''}</span>
                )}
                <span className={`w-2 h-2 rounded-full ${d.online ? 'bg-green-400' : 'bg-white/20'}`} />
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'sessions' && (
        <div className="space-y-2">
          {sessions.length === 0 && <div className="text-white/30 text-sm">No active sessions</div>}
          {sessions.map(s => (
            <div key={s.session_id} className="border border-white/10 rounded p-3">
              <div className="flex items-center justify-between">
                <div className="text-sm font-mono">{s.session_id}</div>
                <span className={`px-1.5 py-0.5 rounded text-xs ${s.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-white/5 text-white/30'}`}>
                  {s.status}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-1 mt-2 text-xs text-white/40">
                <div>Host: {s.host || '-'}</div>
                <div>Device: {s.device_id || '-'}</div>
                <div>Profile: {s.profile_mode || '-'}</div>
                <div>Surface: {s.interaction_surface || '-'}</div>
                <div>Started: {formatTimestamp(s.started_at)}</div>
                <div>Last Active: {formatTimestamp(s.last_activity)}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'attention' && status && (
        <div className="space-y-4">
          <div className="border border-white/10 rounded p-4">
            <div className="text-center">
              <div className={`text-3xl font-mono ${getAttentionColor(status.attention_state)}`}>
                {status.attention_state.toUpperCase()}
              </div>
              <div className="text-xs text-white/40 mt-1">Current Attention State</div>
            </div>
          </div>

          <div className="border border-white/10 rounded p-3">
            <div className="text-xs text-white/40 uppercase tracking-wider mb-2">Interruptibility Rules</div>
            <div className="space-y-1.5 text-sm">
              {[
                { state: 'focused', level: 'critical_only', desc: 'Only critical alerts pass through' },
                { state: 'available', level: 'normal', desc: 'All notifications surface normally' },
                { state: 'away', level: 'queue', desc: 'Accumulate for return' },
                { state: 'offline', level: 'defer', desc: 'Hold until next session' },
                { state: 'sleeping', level: 'defer', desc: 'Hold until wake' },
              ].map(r => (
                <div
                  key={r.state}
                  className={`flex items-center justify-between p-2 rounded ${status.attention_state === r.state ? 'bg-white/5 border border-white/10' : ''}`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${status.attention_state === r.state ? 'bg-blue-400' : 'bg-white/10'}`} />
                    <span className={getAttentionColor(r.state)}>{r.state}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-white/30">{r.desc}</span>
                    <span className={`px-1.5 py-0.5 rounded text-xs ${getInterruptionBadge(r.level)}`}>{r.level}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-white/10 rounded p-3">
            <div className="text-xs text-white/40 uppercase tracking-wider mb-2">Integration Filters</div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="text-center">
                <div className="text-white/40 text-xs">Tick Loop</div>
                <div className="font-mono mt-1">
                  {status.attention_state === 'focused' ? 'suppress' :
                   status.attention_state === 'available' ? 'normal' :
                   status.attention_state === 'away' ? 'accumulate' : 'defer'}
                </div>
              </div>
              <div className="text-center">
                <div className="text-white/40 text-xs">Normal Alerts</div>
                <div className={`font-mono mt-1 ${status.attention_state === 'available' ? 'text-green-400' : 'text-red-400'}`}>
                  {status.attention_state === 'available' ? 'PASS' : 'BLOCK'}
                </div>
              </div>
              <div className="text-center">
                <div className="text-white/40 text-xs">Critical Alerts</div>
                <div className={`font-mono mt-1 ${['focused', 'available'].includes(status.attention_state) ? 'text-green-400' : 'text-red-400'}`}>
                  {['focused', 'available'].includes(status.attention_state) ? 'PASS' : 'BLOCK'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'history' && (
        <div className="space-y-1">
          {timeline.length === 0 && <div className="text-white/30 text-sm">No presence events yet</div>}
          {[...timeline].reverse().map(e => (
            <div key={e.event_id} className="flex items-center gap-2 py-1.5 border-b border-white/5">
              <span className={`px-1.5 py-0.5 rounded text-xs whitespace-nowrap ${getEventColor(e.event_type)}`}>
                {e.event_type}
              </span>
              <span className="text-sm flex-1">{e.summary}</span>
              <span className="text-xs text-white/30 whitespace-nowrap">{formatTimestamp(e.timestamp)}</span>
            </div>
          ))}
        </div>
      )}

      {!status && !loading && (
        <div className="text-white/30 text-sm text-center py-8">
          No presence data available. Click Capture to take a snapshot.
        </div>
      )}
    </div>
  )
}
