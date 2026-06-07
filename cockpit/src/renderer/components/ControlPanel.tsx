import { useState, useEffect, useCallback } from 'react'
import { ChevronDown, ChevronUp, AlertTriangle, Moon, Sun, Shield } from 'lucide-react'
import { useSystemStore } from '../stores/systemStore'
import { useApprovalStore } from '../stores/approvalStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { usePolling } from '../hooks/usePolling'
import { fetchApi } from '../api/client'

/* ── colour maps ── */
const CONTINUITY_COLORS: Record<string, string> = {
  ACTIVE: 'bg-green-600',
  IDLE: 'bg-yellow-600',
  AWAY: 'bg-orange-600',
  NIGHT_SLEEPING: 'bg-purple-600',
  EXTENDED_ABSENCE: 'bg-purple-600',
  RETURNING: 'bg-blue-600',
  RESUME_BRIEF: 'bg-blue-600',
}

const RISK_COLORS: Record<string, string> = {
  LOW: 'bg-green-600/20 text-green-400 border-green-600/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  HIGH: 'bg-red-500/20 text-red-400 border-red-500/30',
}

const MODE_COLORS: Record<string, string> = {
  EXECUTE: 'bg-cyan/20 text-cyan border-cyan/30',
  PLAN: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  REVIEW: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
}

const STATUS_DOT: Record<string, string> = {
  connected: 'bg-green-400',
  connecting: 'bg-yellow-400',
  disconnected: 'bg-red-500',
}

export function ControlPanel() {
  const [expanded, setExpanded] = useState(false)
  const [continuityState, setContinuityState] = useState('ACTIVE')
  const [riskCeiling, setRiskCeiling] = useState('HIGH')
  const [lifecycleMode, setLifecycleMode] = useState('DAY_CYCLE')
  const [overnightStatus, setOvernightStatus] = useState<{
    safe: number
    pending: number
    blocked: number
  }>({ safe: 0, pending: 0, blocked: 0 })
  const [summaryData, setSummaryData] = useState<any>(null)

  const pulse = useSystemStore((s) => s.pulse)
  const approvals = useApprovalStore((s) => s.approvals)
  const fetchApprovals = useApprovalStore((s) => s.fetchApprovals)
  const mode = useCockpitStore((s) => s.mode)
  const apiStatus = useCockpitStore((s) => s.apiStatus)
  const wsStatus = useCockpitStore((s) => s.wsStatus)

  usePolling(fetchApprovals, 5000, true, 500)

  const pendingApprovals = approvals.filter((a) => a.status === 'pending')

  /* ── workstation data polling ── */
  const fetchWorkstationData = useCallback(async () => {
    try {
      const c = await fetchApi<{ state: string }>('/workstation/continuity')
      setContinuityState(c.state)
    } catch { /* stale is fine */ }

    try {
      const mc = await fetchApi<{ lifecycle_mode: string; risk_ceiling: string }>(
        '/workstation/mode-composite',
      )
      setRiskCeiling(mc.risk_ceiling)
      setLifecycleMode(mc.lifecycle_mode)
    } catch { /* stale is fine */ }

    try {
      const ov = await fetchApi<{
        safe_count: number
        pending_count: number
        blocked_count: number
      }>('/workstation/overnight/status')
      setOvernightStatus({
        safe: ov.safe_count,
        pending: ov.pending_count,
        blocked: ov.blocked_count,
      })
    } catch { /* stale is fine */ }

    try {
      const s = await fetchApi<any>('/command-center/summary')
      setSummaryData(s)
    } catch { /* stale is fine */ }
  }, [])

  useEffect(() => {
    fetchWorkstationData()
    const id = setInterval(fetchWorkstationData, 10000)
    return () => clearInterval(id)
  }, [fetchWorkstationData])

  /* ── mode transition ── */
  const transitionContinuity = async (targetState: string) => {
    try {
      await fetchApi('/workstation/continuity/transition', {
        method: 'POST',
        body: JSON.stringify({ target_state: targetState, reason: 'operator_initiated' }),
      })
      setContinuityState(targetState)
    } catch { /* best-effort */ }
  }

  /* ── derived helpers ── */
  const healthDot =
    pulse && pulse.cpu_percent < 90
      ? 'bg-green-400'
      : pulse && pulse.cpu_percent < 95
        ? 'bg-yellow-400'
        : 'bg-red-500'

  const executingPackets =
    summaryData?.what_is_happening?.executing_packets ?? 0
  const blockedCount = summaryData?.what_is_blocked?.count ?? 0
  const shouldResume = !!summaryData?.what_should_resume_next

  const isSleeping =
    continuityState === 'NIGHT_SLEEPING' || continuityState === 'EXTENDED_ABSENCE'

  return (
    <div className="wv-card mx-4 mt-2 mb-1">
      {/* ── Collapsed: instrument strip ── */}
      <div className="flex items-center gap-2 px-4 py-2 flex-wrap">
        {/* 1. Permission horizon — pill style matching mode badge */}
        <span className="text-[10px] font-bold px-2 py-1 rounded border bg-green-600/20 text-green-400 border-green-600/30">
          {continuityState.replace(/_/g, ' ')}
        </span>

        {/* 2. Mode badge */}
        <span
          className={`text-[10px] font-bold px-2 py-1 rounded border ${MODE_COLORS[mode] ?? MODE_COLORS.EXECUTE}`}
        >
          {mode}
        </span>

        {/* 3. Risk ceiling */}
        <span className={`text-[10px] font-bold px-2 py-1 rounded border ${RISK_COLORS[riskCeiling] ?? RISK_COLORS.HIGH}`}>
          RISK: {riskCeiling}
        </span>

        {/* 4. Pending approvals */}
        {pendingApprovals.length > 0 && (
          <button
            onClick={() => useCockpitStore.getState().setPanel('approvals')}
            className="wv-badge wv-badge-warn cursor-pointer"
          >
            <AlertTriangle size={10} />
            {pendingApprovals.length} approval{pendingApprovals.length > 1 ? 's' : ''}
          </button>
        )}

        {/* 5. Blocked */}
        {blockedCount > 0 && (
          <button
            onClick={() => useCockpitStore.getState().setPanel('work')}
            className="text-[10px] text-red-400 bg-red-500/10 px-2 py-1 rounded cursor-pointer"
          >
            {blockedCount} blocked
          </button>
        )}

        {/* 6. Resume */}
        {shouldResume && (
          <span className="text-[10px] text-blue-400 bg-blue-500/10 px-2 py-1 rounded">
            Resume
          </span>
        )}

        <div className="flex-1" />

        {/* 7. Agent count */}
        <span className="text-[10px] font-mono uppercase text-text-tertiary">
          <span className="text-cyan">{pulse?.active_agents ?? 0}</span> AGENTS
        </span>

        {/* 8. Executing packets */}
        <span className="text-[10px] font-mono uppercase text-text-tertiary">
          <span className="text-cyan">{executingPackets}</span> PACKETS
        </span>

        {/* 9. Expand/collapse — far right */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-1 text-text-tertiary hover:text-cyan transition-colors"
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* ── Expanded: detail grid ── */}
      {expanded && (
        <div className="px-4 pb-3 pt-1 border-t border-border">
          <div className="grid grid-cols-3 gap-4 mt-2">
            {/* Column 1: Approvals */}
            <div>
              <div className="wv-label mb-1">APPROVALS</div>
              {pendingApprovals.length === 0 ? (
                <p className="text-[11px] text-text-secondary">None pending</p>
              ) : (
                pendingApprovals.slice(0, 3).map((a) => (
                  <div key={a.id} className="mb-2">
                    <p className="text-[11px] text-text-primary truncate" title={a.description}>
                      {a.description}
                    </p>
                    <div className="flex gap-1 mt-1">
                      <button
                        onClick={() => useApprovalStore.getState().approve(a.id)}
                        className="text-[10px] px-2 py-1 rounded bg-green-600/20 text-green-400 hover:bg-green-600/40 transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => useApprovalStore.getState().deny(a.id)}
                        className="text-[10px] px-2 py-1 rounded bg-red-600/20 text-red-400 hover:bg-red-600/40 transition-colors"
                      >
                        Deny
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Column 2: Overnight */}
            <div>
              <div className="wv-label mb-1">OVERNIGHT</div>
              <div className="space-y-1 text-[11px] font-mono">
                <p>
                  <span className="text-green-400">Safe:</span>{' '}
                  <span className="text-text-primary">{overnightStatus.safe}</span>
                </p>
                <p>
                  <span className="text-yellow-400">Pending:</span>{' '}
                  <span className="text-text-primary">{overnightStatus.pending}</span>
                </p>
                <p>
                  <span className="text-red-400">Blocked:</span>{' '}
                  <span className="text-text-primary">{overnightStatus.blocked}</span>
                </p>
              </div>
              <div className="mt-2">
                {!isSleeping ? (
                  <button
                    onClick={() => transitionContinuity('NIGHT_SLEEPING')}
                    className="flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-purple-600/20 text-purple-400 hover:bg-purple-600/40 transition-colors"
                  >
                    <Moon size={10} /> Go to Sleep
                  </button>
                ) : (
                  <button
                    onClick={() => transitionContinuity('RETURNING')}
                    className="flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-yellow-600/20 text-yellow-400 hover:bg-yellow-600/40 transition-colors"
                  >
                    <Sun size={10} /> Return
                  </button>
                )}
              </div>
            </div>

            {/* Column 3: Resources */}
            <div>
              <div className="wv-label mb-1">RESOURCES</div>
              <div className="space-y-1 text-[11px] text-text-secondary">
                <p className="flex items-center gap-1">
                  <Shield size={10} className="text-cyan" />
                  Concurrency: 4 (1 heavy)
                </p>
                <p>CC sessions: 2 max</p>
                <p>File locks: active</p>
              </div>
              <p className="text-[10px] text-text-tertiary font-mono mt-1">
                cpu: {pulse?.cpu_percent?.toFixed(0) ?? '—'}% · ram:{' '}
                {pulse?.memory_percent?.toFixed(0) ?? '—'}%
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
