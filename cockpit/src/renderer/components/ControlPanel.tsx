import { useState } from 'react'
import { ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react'
import { useSystemStore } from '../stores/systemStore'
import { useApprovalStore } from '../stores/approvalStore'
import { usePolling } from '../hooks/usePolling'

export function ControlPanel() {
  const [expanded, setExpanded] = useState(false)
  const pulse = useSystemStore((s) => s.pulse)
  const approvals = useApprovalStore((s) => s.approvals)
  const fetchApprovals = useApprovalStore((s) => s.fetchApprovals)

  usePolling(fetchApprovals, 5000)

  const pendingApprovals = approvals.filter((a) => a.status === 'pending')

  return (
    <div className="wv-card mx-4 mt-2 mb-1">
      {/* Collapsed: KPI row */}
      <div className="flex items-center gap-4 px-4 py-2">
        <span className="wv-label">CPU</span>
        <span className="text-cyan font-mono text-sm">{pulse?.cpu_percent?.toFixed(0) ?? '—'}%</span>

        <span className="wv-label">RAM</span>
        <span className="text-cyan font-mono text-sm">{pulse?.memory_percent?.toFixed(0) ?? '—'}%</span>

        <span className="wv-label">AGENTS</span>
        <span className="text-cyan font-mono text-sm">{pulse?.active_agents ?? 0}</span>

        <span className="wv-label">TASKS</span>
        <span className="text-text-primary font-mono text-sm">{pulse?.pending_tasks ?? 0}</span>

        {pendingApprovals.length > 0 && (
          <span className="wv-badge wv-badge-warn">
            <AlertTriangle size={10} />
            {pendingApprovals.length} approval{pendingApprovals.length > 1 ? 's' : ''}
          </span>
        )}

        <div className="flex-1" />

        <button
          onClick={() => setExpanded(!expanded)}
          className="p-1 text-text-tertiary hover:text-cyan transition-colors"
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* Expanded: deeper insights */}
      {expanded && (
        <div className="px-4 pb-3 pt-1 border-t border-border">
          <div className="grid grid-cols-3 gap-4 mt-2">
            <div>
              <div className="wv-label mb-1">NEXT ACTIONS</div>
              <p className="text-[11px] text-text-secondary">
                {pendingApprovals.length > 0
                  ? `Review ${pendingApprovals.length} pending approval(s)`
                  : 'No pending actions'}
              </p>
            </div>
            <div>
              <div className="wv-label mb-1">SYSTEM</div>
              <p className="text-[11px] text-text-secondary">
                Uptime: {pulse?.uptime ? `${Math.floor(pulse.uptime / 3600)}h` : '—'}
                {' · '}Disk: {pulse?.disk_percent?.toFixed(0) ?? '—'}%
              </p>
            </div>
            <div>
              <div className="wv-label mb-1">TRACE RATE</div>
              <p className="text-[11px] text-cyan font-mono">
                {pulse?.trace_rate?.toFixed(1) ?? '0'}/hr
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
