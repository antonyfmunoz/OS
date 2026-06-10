import { useState, useCallback, useEffect, useMemo } from 'react'
import { Camera, PictureInPicture2 } from 'lucide-react'
import { useViewContextStore } from '../stores/viewContextStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { useVisionStore } from '../stores/visionStore'
import { useVisionPopout } from '../components/VisionPopout'
import { ActionRequired, buildActionItems } from '../components/ActionRequired'

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

const CONTINUITY_COLORS: Record<string, string> = {
  ACTIVE: 'text-green-400',
  IDLE: 'text-yellow-400',
  AWAY: 'text-orange-400',
  NIGHT_SLEEPING: 'text-purple-400',
  EXTENDED_ABSENCE: 'text-purple-400',
  RETURNING: 'text-blue-400',
  RESUME_BRIEF: 'text-blue-400',
}

const RISK_CEILING_COLORS: Record<string, string> = {
  LOW: 'text-green-400',
  MEDIUM: 'text-yellow-400',
  HIGH: 'text-red-400',
  CRITICAL: 'text-red-400',
}

interface ReturnBrief {
  what_happened: string
  what_changed: string[]
  what_finished: string[]
  what_failed: string[]
  needs_approval: string[]
}

export function CommandCenterPanel() {
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [continuityState, setContinuityState] = useState('ACTIVE')
  const [riskCeiling, setRiskCeiling] = useState('HIGH')
  const [lifecycleMode, setLifecycleMode] = useState('DAY_CYCLE')
  const [overnightStatus, setOvernightStatus] = useState<{ safe: number; pending: number; blocked: number }>({ safe: 0, pending: 0, blocked: 0 })
  const [returnBrief, setReturnBrief] = useState<ReturnBrief | null>(null)
  const [activeBatchCount, setActiveBatchCount] = useState(0)

  const cameraStatus = useVisionStore((s) => s.cameraStatus)
  const cameraPreset = useVisionStore((s) => s.activePreset)
  const cameraConnected = useVisionStore((s) => s.connected)
  const latestFrameUrl = useVisionStore((s) => s.latestFrameUrl)
  const streaming = useVisionStore((s) => s.streaming)
  const { openPopout } = useVisionPopout()

  const setViewContext = useViewContextStore((s) => s.setContext)
  const setPanel = useCockpitStore((s) => s.setPanel)

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

  useEffect(() => {
    setViewContext({ active_route: 'commandcenter', visible_context_summary: 'Command Center overview' })
  }, [setViewContext])

  useEffect(() => {
    const fetchExtras = async () => {
      try {
        const cRes = await fetch('/api/umh/workstation/continuity')
        if (cRes.ok) { const d = await cRes.json(); setContinuityState(d.state || 'ACTIVE') }
      } catch { /* silent */ }
      try {
        const mRes = await fetch('/api/umh/workstation/mode-composite')
        if (mRes.ok) { const d = await mRes.json(); setRiskCeiling(d.risk_ceiling || 'HIGH'); setLifecycleMode(d.lifecycle_mode || 'DAY_CYCLE') }
      } catch { /* silent */ }
      try {
        const oRes = await fetch('/api/umh/workstation/overnight/status')
        if (oRes.ok) { const d = await oRes.json(); setOvernightStatus({ safe: d.safe_count || 0, pending: d.pending_count || 0, blocked: d.blocked_count || 0 }) }
      } catch { /* silent */ }
      try {
        if (continuityState === 'RETURNING' || continuityState === 'RESUME_BRIEF') {
          const rRes = await fetch('/api/umh/workstation/return-brief')
          if (rRes.ok) { const d = await rRes.json(); setReturnBrief(d) }
        } else { setReturnBrief(null) }
      } catch { /* silent */ }
      try {
        const pRes = await fetch('/api/umh/command-center/work-packets?limit=200')
        if (pRes.ok) {
          const d = await pRes.json()
          const batches = (d.packets || []).filter((p: any) => p.child_packet_ids?.length > 0)
          setActiveBatchCount(batches.length)
        }
      } catch { /* silent */ }
    }
    fetchExtras()
    const id = setInterval(fetchExtras, 10000)
    return () => clearInterval(id)
  }, [continuityState])

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

  const actionItems = useMemo(
    () => buildActionItems(summary, {
      onApprovalClick: () => setPanel('approvals'),
      onBlockedClick: () => setPanel('work'),
    }),
    [summary, setPanel]
  )

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

      {/* Action Required */}
      <ActionRequired items={actionItems} loading={loading} />

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

      {/* Vision */}
      <Section title="Vision">
        <div className="flex gap-3">
          {/* Inline camera thumbnail */}
          <button
            onClick={() => setPanel('vision')}
            className="relative w-32 h-20 rounded border overflow-hidden bg-black flex-shrink-0 group"
            style={{ borderColor: streaming ? 'rgba(255,61,61,0.3)' : '#2A2A2A' }}
            title="Open Vision panel"
          >
            {latestFrameUrl ? (
              <img src={latestFrameUrl} alt="Camera" className="w-full h-full object-cover" />
            ) : (
              <div className="flex items-center justify-center w-full h-full">
                <Camera size={16} className="text-gray-600 opacity-30" />
              </div>
            )}
            {streaming && (
              <div className="absolute top-0.5 left-0.5 flex items-center gap-1 px-1 py-0.5 rounded bg-red-500/20 text-[8px] text-red-400 uppercase tracking-wider">
                <span className="w-1 h-1 rounded-full bg-red-400 animate-pulse" />
                live
              </div>
            )}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
              <span className="text-[9px] text-white uppercase tracking-wider">Open</span>
            </div>
          </button>

          {/* Status + controls */}
          <div className="flex-1 flex flex-col justify-between">
            <div>
              <div className="text-[10px] text-gray-300">
                {cameraStatus === 'live' ? 'Camera active' : cameraStatus === 'connecting' ? 'Connecting...' : 'Camera off'}
                {cameraPreset && <span className="text-cyan-400 ml-1">({cameraPreset})</span>}
              </div>
              <div className="text-[10px] text-gray-500">
                {cameraConnected ? 'Vision relay connected' : 'Vision relay disconnected'}
              </div>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <button
                onClick={() => setPanel('vision')}
                className="text-[9px] text-cyan-400 hover:underline uppercase tracking-wider"
              >
                Full view
              </button>
              <button
                onClick={openPopout}
                className="flex items-center gap-1 text-[9px] text-gray-400 hover:text-white uppercase tracking-wider transition-colors"
                title="Pop out into separate window"
              >
                <PictureInPicture2 size={10} />
                Pop out
              </button>
            </div>
          </div>
        </div>
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

      {/* Permission Horizon */}
      <Section title="Permission Horizon">
        <div className="flex items-center gap-3 flex-wrap">
          <span className={`text-sm font-bold ${CONTINUITY_COLORS[continuityState] || 'text-gray-400'}`}>
            {continuityState}
          </span>
          <span className="text-[10px] text-gray-500">
            {lifecycleMode.replace(/_/g, ' ')} — risk ceiling:{' '}
            <span className={RISK_CEILING_COLORS[riskCeiling] || 'text-gray-400'}>{riskCeiling}</span>
          </span>
        </div>
        <div className="text-[10px] text-gray-400 mt-1">
          {riskCeiling === 'LOW'
            ? 'Safe pre-approved work only. No mutations, no deploys, no external comms.'
            : riskCeiling === 'MEDIUM'
              ? 'Bounded mutations with approval. No deploys or external comms.'
              : 'Full operator-governed execution.'}
        </div>
      </Section>

      {/* Autonomous Work (conditional) */}
      {(continuityState === 'NIGHT_SLEEPING' || continuityState === 'EXTENDED_ABSENCE') && (
        <Section title="Autonomous Work">
          <div className="text-[10px] text-purple-300 mb-1">System is running autonomously</div>
          <div className="flex gap-3">
            <span className="text-green-400">{overnightStatus.safe} safe</span>
            <span className="text-yellow-400">{overnightStatus.pending} pending</span>
            <span className="text-red-400">{overnightStatus.blocked} blocked</span>
          </div>
        </Section>
      )}

      {/* Return Brief (conditional) */}
      {returnBrief && (continuityState === 'RETURNING' || continuityState === 'RESUME_BRIEF') && (
        <Section title="Return Brief">
          {returnBrief.what_happened && (
            <div className="text-[10px] text-gray-300 mb-1">{returnBrief.what_happened}</div>
          )}
          {returnBrief.what_finished?.length > 0 && (
            <div className="text-[10px] text-green-400">Finished: {returnBrief.what_finished.join(', ')}</div>
          )}
          {returnBrief.what_failed?.length > 0 && (
            <div className="text-[10px] text-red-400">Failed: {returnBrief.what_failed.join(', ')}</div>
          )}
          {returnBrief.needs_approval?.length > 0 && (
            <div className="text-[10px] text-yellow-400">Needs approval: {returnBrief.needs_approval.join(', ')}</div>
          )}
          {returnBrief.what_changed?.length > 0 && (
            <div className="text-[10px] text-gray-400 mt-1">Changed: {returnBrief.what_changed.join(', ')}</div>
          )}
        </Section>
      )}

      {/* Active Batches */}
      {activeBatchCount > 0 && (
        <Section title="Active Batches">
          <button
            onClick={() => setPanel('work')}
            className="text-[10px] text-cyan-400 hover:underline"
          >
            {activeBatchCount} active batch{activeBatchCount !== 1 ? 'es' : ''} → View in Work panel
          </button>
        </Section>
      )}

      {/* Checkpoint */}
      {cp && cp.last_checkpoint_id && (
        <Section title="Checkpoint">
          <div className="text-[10px] space-y-1 text-gray-400">
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
