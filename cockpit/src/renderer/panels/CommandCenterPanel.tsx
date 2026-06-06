import { useState, useCallback, useEffect, useRef } from 'react'

interface SummaryData {
  ok: boolean
  checkpoint?: {
    last_checkpoint_id: string
    continuity_state: string
    lifecycle_mode: string
    active_node: string
    active_environment: string
    open_loops: string[]
    recommended_next_action: string
    transition_reason: string
  }
  what_is_happening?: {
    continuity_state: string
    active_agents: number
    idle_agents: number
    total_agents: number
    executing_packets: number
  }
  who_is_working?: { agent_id: string; role: string; status: string }[]
  what_is_blocked?: { count: number; items: { id: string; title: string; blockers: string[] }[] }
  what_needs_approval?: { count: number; items: { id: string; title: string; risk_level: string }[] }
  what_finished?: { recent_completed: number; latest: string }
  what_failed?: { recent_failed: number; latest: string }
  what_should_resume_next?: { packet_id: string; title: string; status: string } | null
  source_env?: string
  node?: string
}

interface CommandResult {
  ok: boolean
  intent: string
  governance: string
  response_text: string
  panel_target?: string
  data?: Record<string, unknown>
}

export function CommandCenterPanel() {
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [commandText, setCommandText] = useState('')
  const [commandResult, setCommandResult] = useState<CommandResult | null>(null)
  const [commandLoading, setCommandLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch('/api/umh/command-center/summary')
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      setSummary(data)
      setError('')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'fetch failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSummary()
    const id = setInterval(fetchSummary, 10000)
    return () => clearInterval(id)
  }, [fetchSummary])

  const sendCommand = useCallback(async () => {
    if (!commandText.trim()) return
    setCommandLoading(true)
    try {
      const res = await fetch('/api/umh/presence/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: commandText, source: 'commandcenter' }),
      })
      const data = await res.json()
      setCommandResult(data)
      setCommandText('')
      fetchSummary()
    } catch {
      setCommandResult({ ok: false, intent: 'error', governance: '', response_text: 'Command failed' })
    } finally {
      setCommandLoading(false)
    }
  }, [commandText, fetchSummary])

  const handleApproval = useCallback(async (id: string, decision: 'approved' | 'denied') => {
    try {
      const res = await fetch(`/api/umh/command-center/approvals/${id}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, decided_by: 'operator' }),
      })
      await res.json()
      fetchSummary()
    } catch { /* swallow — refresh will show state */ }
  }, [fetchSummary])

  if (loading) return <div className="p-4 text-xs font-mono text-gray-400">Loading command center...</div>
  if (error) return <div className="p-4 text-xs font-mono text-red-400">Error: {error}</div>
  if (!summary) return null

  const wih = summary.what_is_happening
  const cp = summary.checkpoint

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full text-xs font-mono">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-cyan-400">Command Center</h2>
        <span className="text-gray-500">{summary.source_env}:{summary.node}</span>
      </div>

      {/* Jarvis Input Bar */}
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={commandText}
          onChange={(e) => setCommandText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendCommand()}
          placeholder="Type a Jarvis command..."
          disabled={commandLoading}
          className="flex-1 px-3 py-1.5 bg-gray-900 border border-gray-700 rounded text-white placeholder-gray-500 focus:border-cyan-500 focus:outline-none"
        />
        <button
          onClick={sendCommand}
          disabled={commandLoading || !commandText.trim()}
          className="px-3 py-1.5 bg-cyan-900 border border-cyan-700 rounded text-cyan-300 hover:bg-cyan-800 disabled:opacity-50"
        >
          {commandLoading ? '...' : 'Send'}
        </button>
      </div>

      {/* Command Result */}
      {commandResult && (
        <div className={`p-2 rounded border ${commandResult.ok ? 'border-cyan-800 bg-cyan-950' : 'border-red-800 bg-red-950'}`}>
          <div className="flex gap-3 text-[10px]">
            <span className="text-gray-400">intent: <span className="text-white">{commandResult.intent}</span></span>
            <span className="text-gray-400">governance: <span className={commandResult.governance === 'requires_governance' ? 'text-yellow-400' : 'text-green-400'}>{commandResult.governance}</span></span>
            {commandResult.panel_target && <span className="text-gray-400">panel: <span className="text-white">{commandResult.panel_target}</span></span>}
          </div>
          <div className="mt-1 text-gray-300">{commandResult.response_text}</div>
        </div>
      )}

      {/* What Is Happening */}
      <Section title="What is happening?">
        <div className="grid grid-cols-4 gap-2">
          <Stat label="Active" value={wih?.active_agents ?? 0} color="green" />
          <Stat label="Idle" value={wih?.idle_agents ?? 0} color="gray" />
          <Stat label="Total" value={wih?.total_agents ?? 0} color="cyan" />
          <Stat label="Executing" value={wih?.executing_packets ?? 0} color="yellow" />
        </div>
        {cp && cp.continuity_state && (
          <div className="mt-1 text-[10px] text-gray-500">
            state: {cp.continuity_state} | node: {cp.active_node || summary.node} | env: {cp.active_environment || summary.source_env}
            {cp.recommended_next_action && <> | next: {cp.recommended_next_action}</>}
          </div>
        )}
      </Section>

      {/* Who Is Working */}
      <Section title="Who is working?">
        {summary.who_is_working?.map((a) => (
          <div key={a.agent_id} className="flex justify-between text-[10px]">
            <span className="text-gray-300">{a.agent_id}</span>
            <span className="text-gray-500">{a.role}</span>
            <span className={a.status === 'active' ? 'text-green-400' : 'text-gray-600'}>{a.status}</span>
          </div>
        ))}
      </Section>

      {/* What Is Blocked */}
      <Section title={`What is blocked? (${summary.what_is_blocked?.count ?? 0})`}>
        {summary.what_is_blocked?.items?.map((b) => (
          <div key={b.id} className="text-[10px] text-yellow-400">
            {b.title || b.id} {b.blockers?.length > 0 && <span className="text-gray-500">({b.blockers.join(', ')})</span>}
          </div>
        ))}
        {(summary.what_is_blocked?.count ?? 0) === 0 && <div className="text-[10px] text-gray-600">Nothing blocked</div>}
      </Section>

      {/* What Needs Approval */}
      <Section title={`What needs approval? (${summary.what_needs_approval?.count ?? 0})`}>
        {summary.what_needs_approval?.items?.map((a) => (
          <div key={a.id} className="flex items-center gap-2 text-[10px]">
            <span className="text-orange-400 flex-1">{a.title || a.id}</span>
            <span className="text-gray-500">{a.risk_level}</span>
            <button onClick={() => handleApproval(a.id, 'approved')} className="px-1 bg-green-900 text-green-300 rounded hover:bg-green-800">approve</button>
            <button onClick={() => handleApproval(a.id, 'denied')} className="px-1 bg-red-900 text-red-300 rounded hover:bg-red-800">deny</button>
          </div>
        ))}
        {(summary.what_needs_approval?.count ?? 0) === 0 && <div className="text-[10px] text-gray-600">No pending approvals</div>}
      </Section>

      {/* What Finished / Failed */}
      <div className="grid grid-cols-2 gap-2">
        <Section title="What finished?">
          <Stat label="Recent" value={summary.what_finished?.recent_completed ?? 0} color="green" />
          {summary.what_finished?.latest && <div className="text-[10px] text-gray-400 mt-1">{summary.what_finished.latest}</div>}
        </Section>
        <Section title="What failed?">
          <Stat label="Recent" value={summary.what_failed?.recent_failed ?? 0} color="red" />
          {summary.what_failed?.latest && <div className="text-[10px] text-red-400 mt-1">{summary.what_failed.latest}</div>}
        </Section>
      </div>

      {/* Resume Next */}
      <Section title="What should resume next?">
        {summary.what_should_resume_next ? (
          <div className="text-[10px]">
            <span className="text-cyan-400">{summary.what_should_resume_next.title}</span>
            <span className="text-gray-500 ml-2">{summary.what_should_resume_next.status}</span>
          </div>
        ) : (
          <div className="text-[10px] text-gray-600">No resume target</div>
        )}
      </Section>

      {/* Checkpoint */}
      {cp && cp.last_checkpoint_id && (
        <Section title="Checkpoint">
          <div className="text-[10px] space-y-0.5 text-gray-400">
            <div>id: {cp.last_checkpoint_id.slice(0, 16)}...</div>
            <div>state: {cp.continuity_state} | mode: {cp.lifecycle_mode || 'n/a'}</div>
            {cp.open_loops?.length > 0 && <div>open loops: {cp.open_loops.join(', ')}</div>}
            {cp.transition_reason && <div>reason: {cp.transition_reason}</div>}
          </div>
        </Section>
      )}

      <div className="text-[10px] text-gray-600 pt-2 border-t border-gray-800">
        Auto-refresh: 10s | Packets: {summary.total_packets ?? 0}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-gray-800 rounded p-2">
      <div className="text-[10px] text-gray-400 mb-1 uppercase tracking-wider">{title}</div>
      {children}
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    green: 'text-green-400',
    red: 'text-red-400',
    yellow: 'text-yellow-400',
    cyan: 'text-cyan-400',
    gray: 'text-gray-400',
  }
  return (
    <div className="text-center">
      <div className={`text-lg font-bold ${colors[color] || 'text-white'}`}>{value}</div>
      <div className="text-[10px] text-gray-500">{label}</div>
    </div>
  )
}
