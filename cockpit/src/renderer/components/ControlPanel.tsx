import { useCallback, useState, useEffect } from 'react'
import { ChevronDown, ChevronUp, Moon, Sun, Shield, Hammer, PlayCircle, GitBranch, FileText, AlertCircle, Clock, X } from 'lucide-react'
import { useSystemStore } from '../stores/systemStore'
import { useUnifiedApprovalStore } from '../stores/unifiedApprovalStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { useCollapseStore } from '../stores/collapseStore'
import { fetchApi } from '../api/client'
import { useChatStore } from '../stores/chatStore'
import { useWorkspaceContextStore } from '../stores/workspaceContextStore'
import { useExecutionSummaryStore } from '../stores/executionSummaryStore'
import { useUnifiedWorkstationStore } from '../stores/unifiedWorkstationStore'
import { useEngineeringStore } from '../stores/engineeringStore'
import { useIsMobile } from '../hooks/useIsMobile'

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
  const legacyPending = useUnifiedApprovalStore((s) => s.pending)
  const unifiedPending = useUnifiedApprovalStore((s) => s.byUrgency)
  const unifiedApprove = useUnifiedApprovalStore((s) => s.approve)
  const unifiedReject = useUnifiedApprovalStore((s) => s.reject)
  const mobile = useIsMobile()
  const mode = useCockpitStore((s) => s.mode)
  const apiStatus = useCockpitStore((s) => s.apiStatus)
  const wsStatus = useCockpitStore((s) => s.wsStatus)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const allPlans = useEngineeringStore((s) => s.plans)
  const storeFetchPlans = useEngineeringStore((s) => s.fetchPlans)

  /* ── Resume snapshot ── */
  const [resumeSnapshot, setResumeSnapshot] = useState<{
    active_project?: string; active_branch?: string; active_file?: string
    current_objective?: string; last_execution_status?: string
    last_execution_ago?: string; pending_approvals?: number
    next_action?: string; since_away?: string[]
  } | null>(null)
  const [resumeDismissed, setResumeDismissed] = useState(false)
  const setPanel = useCockpitStore((s) => s.setPanel)
  const setActiveProject = useWorkspaceContextStore((s) => s.setActiveProject)
  const setActiveFile = useWorkspaceContextStore((s) => s.setActiveFile)
  const setActiveBranch = useWorkspaceContextStore((s) => s.setActiveBranch)

  useEffect(() => {
    const lastDismissed = localStorage.getItem('umh-resume-dismissed-at')
    if (lastDismissed && Date.now() - parseInt(lastDismissed, 10) < 60_000) {
      setResumeDismissed(true)
      return
    }
    fetchApi<Record<string, unknown>>('/workstation/resume')
      .then((data: any) => {
        if (data.active_project || data.active_file || data.current_objective) {
          setResumeSnapshot(data)
        }
      })
      .catch(() => {})
  }, [])

  const handleResume = useCallback(() => {
    if (resumeSnapshot) {
      if (resumeSnapshot.active_project) setActiveProject(resumeSnapshot.active_project)
      if (resumeSnapshot.active_file) setActiveFile(resumeSnapshot.active_file)
      if (resumeSnapshot.active_branch) setActiveBranch(resumeSnapshot.active_branch)
      setPanel('editor')
    }
    setResumeDismissed(true)
    localStorage.setItem('umh-resume-dismissed-at', String(Date.now()))
  }, [resumeSnapshot, setActiveProject, setActiveFile, setActiveBranch, setPanel])

  const handleDismissResume = useCallback(() => {
    setResumeDismissed(true)
    localStorage.setItem('umh-resume-dismissed-at', String(Date.now()))
  }, [])

  const engineeringPlans = allPlans.filter((p) => p.status === 'draft' || p.status === 'approved')


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

  const pendingApprovals = legacyPending.filter((a) => a.status === 'pending')
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
    <div className={`wv-card absolute ${mobile ? 'z-30' : 'z-20'}`} style={{ top: 6, left: mobile ? 6 : 172, right: mobile ? 6 : 252 }}>
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

        {/* 8. Approvals (unified + legacy) — this strip IS the cockpit's top HUD
            approval control (mounted directly under the title bar in Shell). The
            wg-hud-approvals alias marks the pending-count badge for the field
            harness; the expand toggle below opens the approval list. */}
        <span data-testid="wg-hud-approvals" className="text-[10px] font-mono uppercase text-text-tertiary">
          APPROVALS <span className={totalPending > 0 ? 'text-yellow-400' : 'text-text-tertiary'}>{totalPending}</span>
        </span>

        {/* 9. Blocked */}
        <span className="text-[10px] font-mono uppercase text-text-tertiary">
          BLOCKED <span className="text-red-400">{blockedCount}</span>
        </span>

        {/* 10. Expand/collapse — far right. This control opens the expanded
            approval list, so it carries the hud-approvals-toggle id the field
            harness drives to reveal the approval rows. */}
        <button
          data-testid="wg-hud-approvals-toggle"
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
                const id = ua.approval_id ?? ua.id ?? `ua-${i}`
                const desc = ua.description ?? ua.title ?? 'Pending approval'
                const source = ua.source_type ?? ''
                // Objective-plan approvals carry plan context in `details`
                // ({plan_record_id, objective_id, graph_version, packet_count,
                // conversation_id}). Surface v{n}/packets on the row and give the
                // decision buttons the wg-* testids ONLY for this source, so the
                // field harness anchors to the row whose desc holds its run tag.
                const isPlan = source === 'objective_plan'
                // UnifiedApproval.to_dict() nests plan context under `context.details`.
                const uaContext = (ua.context ?? {}) as Record<string, unknown>
                const details = ((uaContext.details ?? ua.details) ?? {}) as Record<string, unknown>
                const graphVersion = typeof details.graph_version === 'number' ? details.graph_version : undefined
                const packetCount = typeof details.packet_count === 'number' ? details.packet_count : undefined
                return (
                  <div
                    key={id}
                    data-testid="wg-approval-row"
                    data-source-type={source}
                    // Deterministic row anchor: the description is truncated
                    // server-side (300 chars), so text can NOT identify which
                    // plan a row belongs to when descriptions collide — the
                    // field harness (and any operator tooling) anchors by
                    // plan record id instead.
                    {...(isPlan && typeof details.plan_record_id === 'string'
                      ? { 'data-plan-record-id': details.plan_record_id }
                      : {})}
                    className="mb-2"
                  >
                    <div className="flex items-center gap-1 flex-wrap">
                      {source && <span className="text-[9px] px-1 py-0.5 rounded bg-cyan/10 text-cyan font-mono">{source}</span>}
                      {isPlan && graphVersion !== undefined && (
                        <span className="text-[9px] px-1 py-0.5 rounded bg-surface-raised text-text-tertiary font-mono">v{graphVersion}</span>
                      )}
                      {isPlan && packetCount !== undefined && (
                        <span className="text-[9px] px-1 py-0.5 rounded bg-surface-raised text-text-tertiary font-mono">{packetCount} packets</span>
                      )}
                      <p className="text-[11px] text-text-primary truncate" title={desc}>{desc}</p>
                    </div>
                    <div className="flex gap-1 mt-1">
                      <button
                        {...(isPlan ? { 'data-testid': 'wg-approve-btn' } : {})}
                        onClick={() => unifiedApprove(id, source)}
                        className="text-[10px] px-2 py-1 rounded bg-green-600/20 text-green-400 hover:bg-green-600/40 transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        {...(isPlan ? { 'data-testid': 'wg-reject-btn' } : {})}
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
                      onClick={() => unifiedApprove(a.id, a.source_type ?? 'governance', 'operator')}
                      className="text-[10px] px-2 py-1 rounded bg-green-600/20 text-green-400 hover:bg-green-600/40 transition-colors"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => unifiedReject(a.id, a.source_type ?? 'governance', '', 'operator')}
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
          {/* Resume snapshot */}
          {resumeSnapshot && !resumeDismissed && (
            <div className="mt-3 pt-2 border-t border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="wv-label">RESUME</span>
                <button onClick={handleDismissResume} className="p-0.5 text-text-tertiary hover:text-text-secondary">
                  <X size={10} />
                </button>
              </div>
              <div className="space-y-1 text-[11px]">
                {resumeSnapshot.current_objective && (
                  <div className="flex items-center gap-1.5">
                    <AlertCircle size={10} className="text-text-tertiary shrink-0" />
                    <span className="text-text-secondary truncate">{resumeSnapshot.current_objective}</span>
                  </div>
                )}
                {resumeSnapshot.active_project && (
                  <div className="flex items-center gap-1.5">
                    <FileText size={10} className="text-text-tertiary shrink-0" />
                    <span className="text-text-secondary truncate">{resumeSnapshot.active_project}</span>
                  </div>
                )}
                {resumeSnapshot.active_branch && (
                  <div className="flex items-center gap-1.5">
                    <GitBranch size={10} className="text-text-tertiary shrink-0" />
                    <span className="text-text-secondary truncate">{resumeSnapshot.active_branch}</span>
                  </div>
                )}
                {resumeSnapshot.last_execution_status && (
                  <div className="flex items-center gap-1.5">
                    <Clock size={10} className="text-text-tertiary shrink-0" />
                    <span className="text-text-secondary">{resumeSnapshot.last_execution_status} {resumeSnapshot.last_execution_ago}</span>
                  </div>
                )}
                {resumeSnapshot.next_action && (
                  <div className="flex items-center gap-1.5">
                    <PlayCircle size={10} className="text-cyan shrink-0" />
                    <span className="text-cyan font-medium truncate">{resumeSnapshot.next_action}</span>
                  </div>
                )}
              </div>
              <button
                onClick={handleResume}
                className="flex items-center gap-1 mt-2 px-2 py-1 rounded text-[10px] font-medium"
                style={{ background: 'var(--color-accent)', color: '#000' }}
              >
                <PlayCircle size={10} />
                Resume
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
