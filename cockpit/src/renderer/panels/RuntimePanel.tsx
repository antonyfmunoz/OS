import { useEffect, useState, useCallback } from 'react'
import { fetchApi } from '../api/client'

interface RuntimeOverview {
  total_sessions: number
  active_sessions: number
  completed_sessions: number
  failed_sessions: number
  blocked_sessions: number
  by_status: Record<string, number>
  adapters: Record<string, AdapterInfo>
}

interface AdapterInfo {
  available: boolean
  adapter_id: string
  runtime_type: string
  [key: string]: unknown
}

interface RuntimeSessionData {
  session_id: string
  runtime_type: string
  runtime_status: string
  work_packet_id: string
  workcell_id: string
  command: string
  risk_class: string
  started_at: number
  completed_at: number
  stopped_at: number
  failure_reason: string
  stop_reason: string
}

interface RuntimeEventData {
  event_id: string
  session_id: string
  event_type: string
  timestamp: number
  message: string
  stream: string
  sequence: number
  severity: string
}

interface HandoffPreview {
  preview_id: string
  work_packet_id: string
  recommended_runtime: string
  reason: string
  risk_class: string
  sandbox_required: boolean
  expected_artifacts: string[]
  validation_plan: string
  approval_required: boolean
  blocked_reason: string
  what_will_happen: string[]
  what_will_not_happen: string[]
  command: string
  prompt: string
}

function usePolling(fn: () => void, intervalMs: number) {
  useEffect(() => {
    fn()
    const id = setInterval(fn, intervalMs)
    return () => clearInterval(id)
  }, [fn, intervalMs])
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    drafted: 'bg-gray-600',
    approved: 'bg-blue-600',
    starting: 'bg-yellow-600',
    running: 'bg-green-600',
    waiting_for_input: 'bg-yellow-500',
    stopping: 'bg-orange-600',
    stopped: 'bg-orange-500',
    completed: 'bg-emerald-600',
    failed: 'bg-red-600',
    blocked: 'bg-red-500',
    expired: 'bg-gray-500',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono ${colors[status] || 'bg-gray-600'}`}>
      {status}
    </span>
  )
}

function Spinner() {
  return <span className="animate-spin inline-block w-4 h-4 border-2 border-t-transparent border-white/60 rounded-full" />
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between py-1 border-b border-white/5">
      <span className="text-white/50 text-sm">{label}</span>
      <span className="text-sm font-mono">{value}</span>
    </div>
  )
}

export function RuntimePanel() {
  const [overview, setOverview] = useState<RuntimeOverview | null>(null)
  const [sessions, setSessions] = useState<RuntimeSessionData[]>([])
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [events, setEvents] = useState<RuntimeEventData[]>([])
  const [handoff, setHandoff] = useState<HandoffPreview | null>(null)
  const [handoffInput, setHandoffInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadOverview = useCallback(async () => {
    try {
      const data = await fetchApi<RuntimeOverview>('/organism/runtime-surface')
      setOverview(data)
    } catch (e) {
      setError((e as Error).message)
    }
  }, [])

  const loadSessions = useCallback(async () => {
    try {
      const data = await fetchApi<{ sessions: RuntimeSessionData[] }>('/organism/runtime-surface/sessions')
      setSessions(data.sessions || [])
    } catch (e) {
      setError((e as Error).message)
    }
  }, [])

  const loadEvents = useCallback(async (sessionId: string) => {
    try {
      const data = await fetchApi<{ events: RuntimeEventData[] }>(
        `/organism/runtime-surface/sessions/${sessionId}/events`
      )
      setEvents(data.events || [])
    } catch (e) {
      setError((e as Error).message)
    }
  }, [])

  usePolling(loadOverview, 15000)
  usePolling(loadSessions, 15000)

  useEffect(() => {
    if (selectedSession) {
      loadEvents(selectedSession)
      const id = setInterval(() => loadEvents(selectedSession), 5000)
      return () => clearInterval(id)
    }
    return undefined
  }, [selectedSession, loadEvents])

  const requestHandoff = async () => {
    if (!handoffInput.trim()) return
    setLoading(true)
    try {
      const data = await fetchApi<HandoffPreview>('/organism/runtime-surface/handoff-preview', {
        method: 'POST',
        body: JSON.stringify({ input: handoffInput, intent_type: 'create_work' }),
      })
      setHandoff(data)
    } catch (e) {
      setError((e as Error).message)
    }
    setLoading(false)
  }

  const stopSession = async (sessionId: string) => {
    try {
      await fetchApi('/organism/runtime-surface/sessions/' + sessionId + '/stop', {
        method: 'POST',
        body: JSON.stringify({ reason: 'operator_requested' }),
      })
      loadSessions()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Runtime Surface</h1>
        <span className="text-xs px-3 py-1 rounded bg-amber-900/50 text-amber-300 border border-amber-700/50">
          sandbox only — no main mutation — no merge — no production truth update
        </span>
      </div>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700/50 rounded text-red-300 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {/* Overview */}
      {overview && (
        <section className="grid grid-cols-5 gap-3">
          <div className="p-3 bg-white/5 rounded border border-white/10">
            <div className="text-2xl font-bold">{overview.total_sessions}</div>
            <div className="text-xs text-white/50">total sessions</div>
          </div>
          <div className="p-3 bg-white/5 rounded border border-white/10">
            <div className="text-2xl font-bold text-green-400">{overview.active_sessions}</div>
            <div className="text-xs text-white/50">active</div>
          </div>
          <div className="p-3 bg-white/5 rounded border border-white/10">
            <div className="text-2xl font-bold text-emerald-400">{overview.completed_sessions}</div>
            <div className="text-xs text-white/50">completed</div>
          </div>
          <div className="p-3 bg-white/5 rounded border border-white/10">
            <div className="text-2xl font-bold text-red-400">{overview.failed_sessions}</div>
            <div className="text-xs text-white/50">failed</div>
          </div>
          <div className="p-3 bg-white/5 rounded border border-white/10">
            <div className="text-2xl font-bold text-orange-400">{overview.blocked_sessions}</div>
            <div className="text-xs text-white/50">blocked</div>
          </div>
        </section>
      )}

      {/* Adapters */}
      {overview?.adapters && (
        <section className="bg-white/5 rounded border border-white/10 p-4">
          <h2 className="text-sm font-semibold mb-2 text-white/70">Available Adapters</h2>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(overview.adapters).map(([key, info]) => (
              <div key={key} className="flex items-center gap-2 text-sm">
                <span className={`w-2 h-2 rounded-full ${info.available ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="font-mono">{key}</span>
                <span className="text-white/40">—</span>
                <span className="text-white/50">{info.available ? 'ready' : 'unavailable'}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Handoff Preview */}
      <section className="bg-white/5 rounded border border-white/10 p-4">
        <h2 className="text-sm font-semibold mb-2 text-white/70">Runtime Handoff Preview</h2>
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={handoffInput}
            onChange={(e) => setHandoffInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && requestHandoff()}
            placeholder="Describe what you want the runtime to do..."
            className="flex-1 bg-white/5 border border-white/10 rounded px-3 py-2 text-sm"
          />
          <button
            onClick={requestHandoff}
            disabled={loading || !handoffInput.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded text-sm"
          >
            {loading ? <Spinner /> : 'Preview'}
          </button>
        </div>
        {handoff && (
          <div className="space-y-2 text-sm">
            <Row label="Runtime" value={handoff.recommended_runtime} />
            <Row label="Risk" value={handoff.risk_class} />
            <Row label="Sandbox" value={handoff.sandbox_required ? 'yes' : 'no'} />
            <Row label="Approval" value={handoff.approval_required ? 'required' : 'not required'} />
            {handoff.blocked_reason && (
              <Row label="Blocked" value={<span className="text-red-400">{handoff.blocked_reason}</span>} />
            )}
            {handoff.what_will_happen.length > 0 && (
              <div className="mt-2">
                <div className="text-white/50 text-xs mb-1">What will happen:</div>
                <ul className="list-disc list-inside text-white/70 text-xs space-y-0.5">
                  {handoff.what_will_happen.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </div>
            )}
            {handoff.what_will_not_happen.length > 0 && (
              <div className="mt-2">
                <div className="text-white/50 text-xs mb-1">What will NOT happen:</div>
                <ul className="list-disc list-inside text-red-400/70 text-xs space-y-0.5">
                  {handoff.what_will_not_happen.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Sessions Table */}
      <section className="bg-white/5 rounded border border-white/10 p-4">
        <h2 className="text-sm font-semibold mb-2 text-white/70">Runtime Sessions</h2>
        {sessions.length === 0 ? (
          <div className="text-white/30 text-sm py-4 text-center">No runtime sessions yet</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-white/40 text-xs border-b border-white/10">
                  <th className="text-left py-1 pr-3">Session</th>
                  <th className="text-left py-1 pr-3">Type</th>
                  <th className="text-left py-1 pr-3">Status</th>
                  <th className="text-left py-1 pr-3">Work Packet</th>
                  <th className="text-left py-1 pr-3">Risk</th>
                  <th className="text-left py-1 pr-3">Started</th>
                  <th className="text-left py-1"></th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr
                    key={s.session_id}
                    className={`border-b border-white/5 cursor-pointer hover:bg-white/5 ${
                      selectedSession === s.session_id ? 'bg-white/10' : ''
                    }`}
                    onClick={() => setSelectedSession(s.session_id)}
                  >
                    <td className="py-2 pr-3 font-mono text-xs">{s.session_id.slice(0, 15)}</td>
                    <td className="py-2 pr-3">{s.runtime_type}</td>
                    <td className="py-2 pr-3"><StatusBadge status={s.runtime_status} /></td>
                    <td className="py-2 pr-3 font-mono text-xs text-white/50">{s.work_packet_id ? s.work_packet_id.slice(0, 15) : '—'}</td>
                    <td className="py-2 pr-3">{s.risk_class}</td>
                    <td className="py-2 pr-3 text-white/50">{s.started_at ? new Date(s.started_at * 1000).toLocaleTimeString() : '—'}</td>
                    <td className="py-2">
                      {['running', 'starting', 'waiting_for_input'].includes(s.runtime_status) && (
                        <button
                          onClick={(e) => { e.stopPropagation(); stopSession(s.session_id) }}
                          className="px-2 py-0.5 bg-red-700 hover:bg-red-600 rounded text-xs"
                        >
                          Stop
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Event Stream */}
      {selectedSession && (
        <section className="bg-white/5 rounded border border-white/10 p-4">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-white/70">
              Events — <span className="font-mono">{selectedSession.slice(0, 15)}</span>
            </h2>
            <button
              onClick={() => setSelectedSession(null)}
              className="text-xs text-white/40 hover:text-white/60"
            >
              close
            </button>
          </div>
          {events.length === 0 ? (
            <div className="text-white/30 text-sm py-2">No events</div>
          ) : (
            <div className="max-h-80 overflow-y-auto space-y-1 font-mono text-xs">
              {events.map((ev) => (
                <div
                  key={ev.event_id}
                  className={`py-1 px-2 rounded ${
                    ev.severity === 'error' ? 'bg-red-900/20 text-red-300' :
                    ev.event_type === 'stdout' ? 'text-green-300/80' :
                    ev.event_type === 'stderr' ? 'text-orange-300/80' :
                    'text-white/60'
                  }`}
                >
                  <span className="text-white/30 mr-2">{new Date(ev.timestamp * 1000).toLocaleTimeString()}</span>
                  <span className="text-blue-400/60 mr-2">[{ev.event_type}]</span>
                  {ev.message}
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
