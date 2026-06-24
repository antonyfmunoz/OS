import { useCallback } from 'react'
import { ChevronDown, ChevronUp, Moon, Sun, Shield, Hammer } from 'lucide-react'
import { useSystemStore } from '../stores/systemStore'
import { useApprovalStore } from '../stores/approvalStore'
import { useUnifiedApprovalStore } from '../stores/unifiedApprovalStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { useCollapseStore } from '../stores/collapseStore'
import { usePolling } from '../hooks/usePolling'
import { fetchApi } from '../api/client'
import { useChatStore } from '../stores/chatStore'
import { useExecutionSummaryStore } from '../stores/executionSummaryStore'
import { useUnifiedWorkstationStore } from '../stores/unifiedWorkstationStore'
import { useEngineeringStore } from '../stores/engineeringStore'

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
  const expanded = useCollapseStore((s) => s.isOpen('control-panel'))
  const toggleExpanded = useCollapseStore((s) => s.toggle)

  const pulse = useSystemStore((s) => s.pulse)
  const execSummary = useExecutionSummaryStore((s) => s.summary)
  const wsSnap = useUnifiedWorkstationStore((s) => s.snapshot)
  const continuityState = wsSnap.continuity_state
  const riskCeiling = wsSnap.risk_ceiling
  const overnightStatus = {
    safe: wsSnap.overnight.safe_count,
    pending: wsSnap.overnight.pending_count,
    blocked: wsSnap.overnight.blocked_count,
  }
  const approvals = useApprovalStore((s) => s.approvals)
  const fetchApprovals = useApprovalStore((s) => s.fetchApprovals)
  const unifiedPending = useUnifiedApprovalStore((s) => s.byUrgency)
  const fetchByUrgency = useUnifiedApprovalStore((s) => s.fetchByUrgency)
  const unifiedApprove = useUnifiedApprovalStore((s) => s.approve)
  const unifiedReject = useUnifiedApprovalStore((s) => s.reject)
  const mode = useCockpitStore((s) => s.mode)
  const apiStatus = useCockpitStore((s) => s.apiStatus)
  const wsStatus = useCockpitStore((s) => s.wsStatus)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const allPlans = useEngineeringStore((s) => s.plans)
  const storeFetchPlans = useEngineeringStore((s) => s.fetchPlans)
  const engineeringPlans = allPlans.filter((p) => p.status === 'draft' || p.status === 'approved')

  usePolling(fetchApprovals, 5000, true, 500)
  usePolling(fetchByUrgency, 5000, true, 800)
  usePolling(storeFetchPlans, 5000, true, 1200)

  const approvePlan = useCallback(async (planId: string) => {
    try {
      await fetchApi(`/engineering/plans/${planId}/approve`, { method: 'POST' })
      sendMessage(`Plan ${planId} approved. Dispatching to Beast...`, 'text')
      storeFetchPlans()
      fetchApi(`/engineering/plans/${planId}/dispatch`, {
        method: 'POST',
        body: JSON.stringify({ node_id: 'windows-desktop' }),
      }).then((res) => {
        const r = res as Record<string, unknown>
        sendMessage(`Dispatch complete: ${r.dispatched || 0}/${r.total_tasks || '?'} tasks executed. Proof: ${r.proof_id || 'pending'}`, 'text')
        storeFetchPlans()
      }).catch(() => {
        sendMessage('Dispatch to Beast failed. Check mesh connectivity.', 'text')
      })
    } catch {
      sendMessage('Plan approval failed.', 'text')
    }
  }, [sendMessage, storeFetchPlans])

  const rejectPlan = useCallback(async (planId: string) => {
    try {
      await fetchApi(`/engineering/plans/${planId}/reject`, { method: 'POST' })
      sendMessage(`Plan ${planId} rejected.`, 'text')
      storeFetchPlans()
    } catch {
      sendMessage('Plan rejection failed.', 'text')
    }
  }, [sendMessage, storeFetchPlans])

  const pendingApprovals = approvals.filter((a) => a.status === 'pending')
  const totalPending = pendingApprovals.length + unifiedPending.length + engineeringPlans.length

  /* ── mode transition ── */
  const fetchWorkstationSnapshot = useUnifiedWorkstationStore((s) => s.fetchSnapshot)
  const transitionContinuity = async (targetState: string) => {
    try {
      await fetchApi('/workstation/continuity/transition', {
        method: 'POST',
        body: JSON.stringify({ target_state: targetState, reason: 'operator_initiated' }),
      })
      fetchWorkstationSnapshot()
    } catch { /* best-effort */ }
  }

  /* ── derived helpers ── */
  const healthDot =
    pulse && pulse.cpu_percent < 90
      ? 'bg-green-400'
      : pulse && pulse.cpu_percent < 95
        ? 'bg-yellow-400'
        : 'bg-red-500'

  const executingPackets = execSummary.what_is_happening.executing_packets
  const blockedCount = execSummary.what_is_blocked.count
  const shouldResume = !!execSummary.what_should_resume_next

  const isSleeping =
    continuityState === 'NIGHT_SLEEPING' || continuityState === 'EXTENDED_ABSENCE'

  return (
    <div className="wv-card mx-4 mt-2 mb-1">
      {/* ── Collapsed: instrument strip ── */}
      <div className="flex items-center gap-2 px-4 py-2 flex-wrap">
        {/* 1. Status badge */}
        <span className="text-[10px] font-bold px-2 py-1 rounded border bg-green-600/20 text-green-400 border-green-600/30">
          STATUS: {(continuityState || 'ACTIVE').replace(/_/g, ' ')}
        </span>

        {/* 2. Mode badge */}
        <span
          className={`text-[10px] font-bold px-2 py-1 rounded border ${MODE_COLORS[mode] ?? MODE_COLORS.EXECUTE}`}
        >
          MODE: {mode}
        </span>

        {/* 3. Risk ceiling */}
        <span className={`text-[10px] font-bold px-2 py-1 rounded border ${RISK_COLORS[riskCeiling] ?? RISK_COLORS.HIGH}`}>
          RISK: {riskCeiling}
        </span>

        {/* 4. Resume */}
        {shouldResume && (
          <span className="text-[10px] text-blue-400 bg-blue-500/10 px-2 py-1 rounded">
            Resume
          </span>
        )}

        <div className="flex-1" />

        {/* 6. Agent count */}
        <span className="text-[10px] font-mono uppercase text-text-tertiary">
          AGENTS <span className="text-cyan">{pulse?.active_agents ?? 0}</span>
        </span>

        {/* 7. Executing packets */}
        <span className="text-[10px] font-mono uppercase text-text-tertiary">
          PACKETS <span className="text-cyan">{executingPackets}</span>
        </span>

        {/* 8. Approvals (unified + legacy) */}
        <span className="text-[10px] font-mono uppercase text-text-tertiary">
          APPROVALS <span className={totalPending > 0 ? 'text-yellow-400' : 'text-text-tertiary'}>{totalPending}</span>
        </span>

        {/* 9. Blocked */}
        <span className="text-[10px] font-mono uppercase text-text-tertiary">
          BLOCKED <span className="text-red-400">{blockedCount}</span>
        </span>

        {/* 10. Expand/collapse — far right */}
        <button
          onClick={() => toggleExpanded('control-panel')}
          className="p-1 text-text-tertiary hover:text-cyan transition-colors"
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* ── Expanded: detail grid ── */}
      {/* ── Engineering Plan Notification Banner ── */}
      {engineeringPlans.length > 0 && (
        <div className="mx-4 mb-1">
          {engineeringPlans.slice(0, 2).map((plan: any) => {
            const planId = plan.plan_id ?? plan.id ?? ''
            const goal = plan.intent?.goal ?? plan.goal ?? planId
            const taskCount = plan.tasks?.length ?? 0
            return (
              <div key={planId} className="flex items-center gap-2 px-3 py-1.5 rounded border border-cyan/30 bg-cyan/5 mb-1">
                <Hammer size={12} className="text-cyan shrink-0" />
                <span className="text-[11px] text-text-primary truncate flex-1" title={goal}>
                  {goal}
                </span>
                <span className="text-[9px] font-mono text-text-tertiary shrink-0">{taskCount} tasks</span>
                <button
                  onClick={() => approvePlan(planId)}
                  className="text-[10px] px-2 py-0.5 rounded bg-green-600/20 text-green-400 hover:bg-green-600/40 transition-colors shrink-0"
                >
                  Approve
                </button>
                <button
                  onClick={() => rejectPlan(planId)}
                  className="text-[10px] px-2 py-0.5 rounded bg-red-600/20 text-red-400 hover:bg-red-600/40 transition-colors shrink-0"
                >
                  Reject
                </button>
              </div>
            )
          })}
        </div>
      )}

      {expanded && (
        <div className="px-4 pb-3 pt-1 border-t border-border">
          <div className="grid grid-cols-3 gap-4 mt-2">
            {/* Column 1: Approvals (unified + legacy) */}
            <div>
              <div className="wv-label mb-1">APPROVALS</div>
              {unifiedPending.length > 0 && unifiedPending.slice(0, 3).map((ua, i) => {
                const id = (ua as Record<string, unknown>).approval_id as string ?? (ua as Record<string, unknown>).id as string ?? `ua-${i}`
                const desc = (ua as Record<string, unknown>).description as string ?? (ua as Record<string, unknown>).title as string ?? 'Pending approval'
                const source = (ua as Record<string, unknown>).source_type as string ?? ''
                return (
                  <div key={id} className="mb-2">
                    <div className="flex items-center gap-1">
                      {source && <span className="text-[9px] px-1 py-0.5 rounded bg-cyan/10 text-cyan font-mono">{source}</span>}
                      <p className="text-[11px] text-text-primary truncate" title={desc}>{desc}</p>
                    </div>
                    <div className="flex gap-1 mt-1">
                      <button
                        onClick={() => unifiedApprove(id, source)}
                        className="text-[10px] px-2 py-1 rounded bg-green-600/20 text-green-400 hover:bg-green-600/40 transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => unifiedReject(id, source)}
                        className="text-[10px] px-2 py-1 rounded bg-red-600/20 text-red-400 hover:bg-red-600/40 transition-colors"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                )
              })}
              {pendingApprovals.slice(0, unifiedPending.length > 0 ? 1 : 3).map((a) => (
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
              ))}
              {totalPending === 0 && (
                <p className="text-[11px] text-text-secondary">None pending</p>
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
