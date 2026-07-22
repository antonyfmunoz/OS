import { useEffect, useState, useCallback } from 'react'
import { fetchApi } from '../api/client'
import { ConnectionBanner } from '../components/ConnectionBanner'
import { usePolling } from '../hooks/usePolling'
import { useOperatorLoopStore } from '../stores/operatorLoopStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { useObjectivePlanStore } from '../stores/objectivePlanStore'
import type {
  ExecutionMode,
  ExecutionPlan,
  ExecutionRecordSummary,
  FailureReport,
  ValidationResult,
  RoutingResultData,
  DomainDefinition,
  NextActionsData,
  RealitySnapshot,
} from '../stores/operatorLoopStore'

interface QueueSummary {
  total_packets: number
  by_status: Record<string, number>
  by_domain: Record<string, number>
  human_required: number
  approval_required: number
  blocked: number
  active: number
  completed: number
  next_best: PacketSafe | null
}

interface PacketSafe {
  packet_id: string
  title: string
  user_intent: string
  desired_end_state: string
  domain: string
  subdomain: string
  project: string
  company: string
  product: string
  leverage_score: number
  effectiveness_score: number
  efficiency_score: number
  risk_class: string
  priority: number
  urgency: number
  status: string
  status_reason: string
  human_required_actions: string[]
  approval_gates: string[]
  delegation_topology_id: string
  linked_roadmap_phase: string
  blockers: string[]
  source_type: string
  source_id: string
  created_at: number
  updated_at: number
}

const STATUS_COLOR: Record<string, string> = {
  drafted: 'text-text-secondary',
  classified: 'text-cyan',
  planned: 'text-cyan',
  ready_for_review: 'text-warn',
  approval_pending: 'text-warn',
  approved: 'text-ok',
  delegated: 'text-cyan',
  executing: 'text-cyan',
  reconverging: 'text-warn',
  validating: 'text-warn',
  completed: 'text-ok',
  blocked: 'text-danger',
  rejected: 'text-danger',
  failed: 'text-danger',
  superseded: 'text-text-secondary',
  archived: 'text-text-secondary',
}

const RISK_COLOR: Record<string, string> = {
  low: 'text-ok',
  medium: 'text-warn',
  high: 'text-danger',
  critical: 'text-danger',
}

const KANBAN_COLUMNS = [
  { key: 'backlog', label: 'Backlog', statuses: ['drafted', 'classified'] },
  { key: 'ready', label: 'Ready', statuses: ['planned', 'ready_for_review'] },
  { key: 'approval', label: 'Approval', statuses: ['approval_pending'] },
  { key: 'approved', label: 'Approved', statuses: ['approved', 'delegated'] },
  { key: 'executing', label: 'In Progress', statuses: ['executing', 'reconverging', 'validating'] },
  { key: 'blocked', label: 'Blocked', statuses: ['blocked'] },
  { key: 'done', label: 'Done', statuses: ['completed'] },
  { key: 'failed', label: 'Failed', statuses: ['failed', 'rejected', 'superseded', 'archived'] },
]

type ViewMode = 'kanban' | 'table' | 'detail'

export function UniversalWorkPanel() {
  const [summary, setSummary] = useState<QueueSummary | null>(null)
  const [packets, setPackets] = useState<PacketSafe[]>([])
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('kanban')
  const [showCreate, setShowCreate] = useState(false)
  const [intentText, setIntentText] = useState('')
  const [desiredEndState, setDesiredEndState] = useState('')
  const [createMode, setCreateMode] = useState<ExecutionMode>('validate_only')

  const submitIntent = useOperatorLoopStore((s) => s.submitIntent)
  const approvePacket = useOperatorLoopStore((s) => s.approvePacket)
  const rejectPacket = useOperatorLoopStore((s) => s.rejectPacket)
  const executePacket = useOperatorLoopStore((s) => s.executePacket)
  const completePacket = useOperatorLoopStore((s) => s.completePacket)
  const generatePlan = useOperatorLoopStore((s) => s.generatePlan)
  const approvePlan = useOperatorLoopStore((s) => s.approvePlan)
  const lastExecuteResult = useOperatorLoopStore((s) => s.lastExecuteResult)
  const lastPlan = useOperatorLoopStore((s) => s.lastPlan)
  const executing = useOperatorLoopStore((s) => s.executing)

  // Phase 3: Empire state
  const routeIntent = useOperatorLoopStore((s) => s.routeIntent)
  const fetchDomains = useOperatorLoopStore((s) => s.fetchDomains)
  const fetchNextActions = useOperatorLoopStore((s) => s.fetchNextActions)
  const fetchReality = useOperatorLoopStore((s) => s.fetchReality)
  const domains = useOperatorLoopStore((s) => s.domains)
  const lastRouting = useOperatorLoopStore((s) => s.lastRouting)
  const nextActions = useOperatorLoopStore((s) => s.nextActions)
  const realitySnapshot = useOperatorLoopStore((s) => s.realitySnapshot)
  const domainFilter = useOperatorLoopStore((s) => s.domainFilter)
  const setDomainFilter = useOperatorLoopStore((s) => s.setDomainFilter)

  const refresh = useCallback(async () => {
    const [s, p] = await Promise.all([
      fetchApi<QueueSummary>('/organism/universal-work/summary').catch(() => null),
      fetchApi<PacketSafe[]>('/organism/universal-work/packets?limit=50').catch(() => []),
    ])
    if (s) setSummary(s)
    setPackets(p)
  }, [])

  useEffect(() => { refresh() }, [refresh])
  usePolling(refresh, 8000)

  useEffect(() => {
    fetchDomains()
    fetchNextActions()
    fetchReality()
  }, [])

  const selectPacket = useCallback(async (id: string) => {
    const detail = await fetchApi<Record<string, unknown>>(`/organism/universal-work/packets/${id}`).catch(() => null)
    setSelected(detail)
    setViewMode('detail')
  }, [])

  const handleCreate = async () => {
    if (!intentText.trim()) return
    const routing = await routeIntent(intentText, {
      desired_end_state: desiredEndState,
    })
    if (routing) {
      setIntentText('')
      setDesiredEndState('')
      setShowCreate(false)
      refresh()
    }
  }

  const handleApprove = async (id: string) => {
    await approvePacket(id)
    refresh()
    if (selected && String(selected.packet_id) === id) selectPacket(id)
  }

  const handleReject = async (id: string) => {
    await rejectPacket(id)
    refresh()
  }

  const handleGeneratePlan = async (id: string) => {
    await generatePlan(id)
    refresh()
    if (selected && String(selected.packet_id) === id) selectPacket(id)
  }

  const handleApprovePlan = async (planId: string) => {
    await approvePlan(planId)
  }

  const handleExecute = async (id: string, mode: ExecutionMode = 'validate_only', planId?: string) => {
    await executePacket(id, mode, planId)
    refresh()
    if (selected && String(selected.packet_id) === id) selectPacket(id)
  }

  const handleComplete = async (id: string, success: boolean) => {
    await completePacket(id, success ? 'completed by operator' : 'marked failed by operator', success)
    refresh()
  }

  if (!summary) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <ConnectionBanner />
        <div className="flex items-center justify-center flex-1">
          <span className="text-text-secondary text-sm">Loading work queue...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />

      {/* Header */}
      <div className="flex items-center gap-4 px-4 py-2 flex-shrink-0 border-b border-border">
        <h2 className="text-sm font-semibold text-text-primary">Empire Work Queue</h2>
        <span className="text-xs text-text-secondary">{summary.total_packets} total</span>
        {executing && <span className="text-xs text-cyan animate-pulse">executing...</span>}

        {/* Domain filter */}
        <select value={domainFilter} onChange={(e) => setDomainFilter(e.target.value)}
          className="px-2 py-1 text-[10px] rounded bg-surface border border-border text-text-secondary outline-none"
        >
          <option value="">All Domains</option>
          {domains.map((d) => (
            <option key={d.domain_id} value={d.domain_id}>{d.label}</option>
          ))}
        </select>

        <div className="flex-1" />

        {/* Next actions badge */}
        {nextActions && nextActions.next_actions.length > 0 && (
          <span className="px-2 py-0.5 text-[10px] bg-cyan/10 text-cyan rounded border border-cyan/20">
            {nextActions.next_actions.length} action{nextActions.next_actions.length > 1 ? 's' : ''}
          </span>
        )}
        {nextActions && nextActions.open_approvals > 0 && (
          <span className="px-2 py-0.5 text-[10px] bg-warn/10 text-warn rounded border border-warn/20">
            {nextActions.open_approvals} approval{nextActions.open_approvals > 1 ? 's' : ''}
          </span>
        )}
        {nextActions && nextActions.blocked_count > 0 && (
          <span className="px-2 py-0.5 text-[10px] bg-danger/10 text-danger rounded border border-danger/20">
            {nextActions.blocked_count} blocked
          </span>
        )}

        <div className="flex gap-1">
          {(['kanban', 'table'] as const).map((m) => (
            <button key={m} onClick={() => setViewMode(m)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                viewMode === m ? 'bg-surface-raised text-cyan border border-border' : 'text-text-secondary'
              }`}
            >
              {m === 'kanban' ? 'Kanban' : 'Table'}
            </button>
          ))}
        </div>

        <button onClick={() => setShowCreate(!showCreate)}
          className="px-3 py-1 text-xs font-mono uppercase rounded bg-cyan-glow text-cyan border border-border"
        >
          + New
        </button>
      </div>

      {/* Create form — Empire Router */}
      {showCreate && (
        <div className="px-4 py-3 border-b border-border bg-surface-secondary space-y-2">
          <input value={intentText} onChange={(e) => setIntentText(e.target.value)}
            placeholder="What do you want done? (natural language — any domain)"
            className="w-full px-3 py-2 text-sm rounded bg-surface border border-border text-text-primary outline-none"
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
          />
          <input value={desiredEndState} onChange={(e) => setDesiredEndState(e.target.value)}
            placeholder="Desired end state (optional)"
            className="w-full px-3 py-2 text-xs rounded bg-surface border border-border text-text-secondary outline-none"
          />
          <div className="flex gap-2">
            <button onClick={handleCreate}
              className="px-3 py-1 text-xs rounded bg-cyan-glow text-cyan border border-border"
            >Route Intent</button>
            <button onClick={() => setShowCreate(false)}
              className="px-3 py-1 text-xs rounded text-text-secondary border border-border"
            >Cancel</button>
          </div>
        </div>
      )}

      {/* Last routing result */}
      {lastRouting && (
        <div className="px-4 py-2 border-b border-border bg-surface-secondary/50">
          <RoutingResultBanner routing={lastRouting} onDismiss={() => useOperatorLoopStore.setState({ lastRouting: null })} />
        </div>
      )}

      {/* Next actions bar */}
      {nextActions && nextActions.next_actions.length > 0 && (
        <div className="px-4 py-1.5 border-b border-border bg-cyan/5 flex items-center gap-3 overflow-x-auto">
          <span className="text-[10px] text-cyan font-semibold uppercase shrink-0">Next:</span>
          {nextActions.next_actions.map((a, i) => (
            <span key={i} className="text-[11px] text-text-secondary shrink-0">{a}</span>
          ))}
          {nextActions.active_domains.length > 0 && (
            <span className="text-[10px] text-text-secondary/60 shrink-0 ml-auto">
              Active: {nextActions.active_domains.join(', ')}
            </span>
          )}
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 overflow-auto">
        {viewMode === 'kanban' && (
          <KanbanView packets={domainFilter ? packets.filter((p) => p.domain === domainFilter || p.domain === '') : packets}
            onSelect={selectPacket}
            onApprove={handleApprove} onReject={handleReject}
            onExecute={handleExecute} onComplete={handleComplete}
            onGeneratePlan={handleGeneratePlan} />
        )}
        {viewMode === 'table' && (
          <TableView packets={domainFilter ? packets.filter((p) => p.domain === domainFilter || p.domain === '') : packets}
            onSelect={selectPacket}
            onApprove={handleApprove} onReject={handleReject}
            onExecute={handleExecute} onComplete={handleComplete} />
        )}
        {viewMode === 'detail' && selected && (
          <DetailView packet={selected} onBack={() => setViewMode('kanban')}
            onApprove={handleApprove} onReject={handleReject}
            onExecute={handleExecute} onComplete={handleComplete}
            onGeneratePlan={handleGeneratePlan}
            onApprovePlan={handleApprovePlan}
            lastExecuteResult={lastExecuteResult}
            lastPlan={lastPlan}
            executing={executing} />
        )}
      </div>
    </div>
  )
}

function KanbanView({ packets, onSelect, onApprove, onReject, onExecute, onComplete, onGeneratePlan }: {
  packets: PacketSafe[]
  onSelect: (id: string) => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
  onExecute: (id: string, mode?: ExecutionMode) => void
  onComplete: (id: string, success: boolean) => void
  onGeneratePlan: (id: string) => void
}) {
  return (
    <div data-testid="wg-kanban" className="flex gap-2 p-3 h-full overflow-x-auto">
      {KANBAN_COLUMNS.map((col) => {
        // Case-insensitive status match: objective-plan packets can land as
        // CLASSIFIED / PLANNED (uppercase) while the columns list lowercase
        // statuses. Fold both so plan packets show in Backlog / Ready.
        const colPackets = packets.filter((p) =>
          col.statuses.includes((p.status ?? '').toLowerCase()),
        )
        return (
          <div key={col.key} className="flex-shrink-0 w-56 flex flex-col">
            <div className="flex items-center gap-2 px-2 py-2 mb-1">
              <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">{col.label}</span>
              <span className="text-xs text-text-tertiary">{colPackets.length}</span>
            </div>
            <div className="flex-1 overflow-y-auto space-y-1.5">
              {colPackets.map((pkt) => (
                <KanbanCard key={pkt.packet_id} packet={pkt} onClick={() => onSelect(pkt.packet_id)}
                  onApprove={onApprove} onReject={onReject} onExecute={onExecute}
                  onComplete={onComplete} onGeneratePlan={onGeneratePlan} />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function KanbanCard({ packet, onClick, onApprove, onReject, onExecute, onComplete, onGeneratePlan }: {
  packet: PacketSafe
  onClick: () => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
  onExecute: (id: string, mode?: ExecutionMode) => void
  onComplete: (id: string, success: boolean) => void
  onGeneratePlan: (id: string) => void
}) {
  // Packets materialized from an objective plan carry a source link back to the
  // plan record. Surface an "Open Plan" affordance that navigates to the Work
  // Detail panel and focuses that plan — the contextual Plan/Task inspection
  // surface (never the HUD).
  const fromPlan = packet.source_type === 'objective_plan' && !!packet.source_id
  const openPlan = () => {
    useCockpitStore.getState().setPanel('workdetail')
    const planStore = useObjectivePlanStore.getState()
    planStore.selectPlan(packet.source_id)
    planStore.fetchPlan(packet.source_id)
  }

  return (
    <div data-testid="wg-kanban-card" data-packet-id={packet.packet_id} data-status={packet.status}
         className="border border-border rounded p-2 bg-surface-secondary cursor-pointer hover:border-cyan transition-colors"
         onClick={onClick}>
      <p className="text-xs font-medium text-text-primary truncate mb-1">{packet.title}</p>
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-[10px] font-mono ${RISK_COLOR[packet.risk_class]}`}>{packet.risk_class}</span>
        <span className="text-[10px] text-text-tertiary">{packet.domain}</span>
      </div>
      {packet.approval_gates.length > 0 && (
        <span className="text-[10px] text-warn">approval required</span>
      )}
      {fromPlan && (
        <div className="mt-1" onClick={(e) => e.stopPropagation()}>
          <button
            data-testid="wg-kanban-open-plan"
            onClick={openPlan}
            className="px-2 py-0.5 text-[10px] rounded bg-cyan/10 text-cyan border border-border hover:bg-cyan/20"
          >
            Open Plan
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-1 mt-2" onClick={(e) => e.stopPropagation()}>
        {packet.status === 'approval_pending' && (
          <>
            <button onClick={() => onApprove(packet.packet_id)}
              className="px-2 py-1 text-[10px] rounded bg-ok/10 text-ok border border-border">approve</button>
            <button onClick={() => onReject(packet.packet_id)}
              className="px-2 py-1 text-[10px] rounded bg-danger/10 text-danger border border-border">reject</button>
          </>
        )}
        {(packet.status === 'approved' || (packet.status === 'classified' && packet.approval_gates.length === 0)) && (
          <>
            <button onClick={() => onGeneratePlan(packet.packet_id)}
              className="px-2 py-1 text-[10px] rounded bg-surface-tertiary text-text-secondary border border-border">plan</button>
            <button onClick={() => onExecute(packet.packet_id, 'validate_only')}
              className="px-2 py-1 text-[10px] rounded bg-cyan/10 text-cyan border border-border">validate</button>
            <button onClick={() => onExecute(packet.packet_id, 'implement_and_validate')}
              className="px-2 py-1 text-[10px] rounded bg-ok/10 text-ok border border-border">run</button>
          </>
        )}
        {packet.status === 'validating' && (
          <>
            <button onClick={() => onComplete(packet.packet_id, true)}
              className="px-2 py-1 text-[10px] rounded bg-ok/10 text-ok border border-border">done</button>
            <button onClick={() => onComplete(packet.packet_id, false)}
              className="px-2 py-1 text-[10px] rounded bg-danger/10 text-danger border border-border">fail</button>
          </>
        )}
      </div>
    </div>
  )
}

function TableView({ packets, onSelect, onApprove, onReject, onExecute, onComplete }: {
  packets: PacketSafe[]
  onSelect: (id: string) => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
  onExecute: (id: string, mode?: ExecutionMode) => void
  onComplete: (id: string, success: boolean) => void
}) {
  return (
    <div className="p-3">
      <div className="border border-border rounded overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-surface-secondary text-text-secondary">
              <th className="px-2 py-2 text-left">Status</th>
              <th className="px-2 py-2 text-left">Title</th>
              <th className="px-2 py-2 text-left">Domain</th>
              <th className="px-2 py-2 text-right">Leverage</th>
              <th className="px-2 py-2 text-left">Risk</th>
              <th className="px-2 py-2 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {packets.map((pkt) => (
              <tr key={pkt.packet_id} className="border-t border-border hover:bg-surface-secondary">
                <td className={`px-2 py-2 cursor-pointer ${STATUS_COLOR[pkt.status]}`}
                    onClick={() => onSelect(pkt.packet_id)}>{pkt.status}</td>
                <td className="px-2 py-2 text-text-primary truncate max-w-[200px] cursor-pointer"
                    onClick={() => onSelect(pkt.packet_id)}>{pkt.title}</td>
                <td className="px-2 py-2 text-text-secondary">{pkt.domain}</td>
                <td className="px-2 py-2 text-right text-cyan">{pkt.leverage_score.toFixed(2)}</td>
                <td className={`px-2 py-2 ${RISK_COLOR[pkt.risk_class]}`}>{pkt.risk_class}</td>
                <td className="px-2 py-2">
                  <div className="flex gap-1 justify-center">
                    {pkt.status === 'approval_pending' && (
                      <>
                        <button onClick={() => onApprove(pkt.packet_id)}
                          className="px-2 py-1 text-[10px] rounded text-ok border border-border">✓</button>
                        <button onClick={() => onReject(pkt.packet_id)}
                          className="px-2 py-1 text-[10px] rounded text-danger border border-border">✗</button>
                      </>
                    )}
                    {(pkt.status === 'approved' || (pkt.status === 'classified' && pkt.approval_gates.length === 0)) && (
                      <button onClick={() => onExecute(pkt.packet_id, 'implement_and_validate')}
                        className="px-2 py-1 text-[10px] rounded text-cyan border border-border">▶</button>
                    )}
                    {pkt.status === 'validating' && (
                      <>
                        <button onClick={() => onComplete(pkt.packet_id, true)}
                          className="px-2 py-1 text-[10px] rounded text-ok border border-border">✓</button>
                        <button onClick={() => onComplete(pkt.packet_id, false)}
                          className="px-2 py-1 text-[10px] rounded text-danger border border-border">✗</button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function DetailView({ packet, onBack, onApprove, onReject, onExecute, onComplete, onGeneratePlan, onApprovePlan, lastExecuteResult, lastPlan, executing }: {
  packet: Record<string, unknown>
  onBack: () => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
  onExecute: (id: string, mode?: ExecutionMode, planId?: string) => void
  onComplete: (id: string, success: boolean) => void
  onGeneratePlan: (id: string) => void
  onApprovePlan: (planId: string) => void
  lastExecuteResult: Record<string, unknown> | null
  lastPlan: ExecutionPlan | null
  executing: boolean
}) {
  const id = String(packet.packet_id || '')
  const status = String(packet.status || '')
  const [selectedMode, setSelectedMode] = useState<ExecutionMode>('implement_and_validate')

  const canExecute = status === 'approved' || (status === 'classified' && (!Array.isArray(packet.approval_gates) || packet.approval_gates.length === 0))
  const activeResult = lastExecuteResult && String((lastExecuteResult as Record<string, unknown>).packet_id) === id ? lastExecuteResult as Record<string, unknown> : null

  return (
    <div className="p-4 space-y-4 max-w-3xl overflow-y-auto">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="text-xs text-text-secondary hover:text-text-primary">← Back</button>
        <h2 className="text-sm font-semibold text-text-primary">{String(packet.title || 'Untitled')}</h2>
        <span className={`text-xs font-mono ${STATUS_COLOR[status]}`}>{status}</span>
        {executing && <span className="text-xs text-cyan animate-pulse">executing...</span>}
      </div>

      {/* Action bar */}
      <div className="flex flex-wrap gap-2">
        {status === 'approval_pending' && (
          <>
            <button onClick={() => onApprove(id)}
              className="px-3 py-2 text-xs rounded bg-ok/10 text-ok border border-border">Approve</button>
            <button onClick={() => onReject(id)}
              className="px-3 py-2 text-xs rounded bg-danger/10 text-danger border border-border">Reject</button>
          </>
        )}
        {canExecute && (
          <>
            <button onClick={() => onGeneratePlan(id)}
              className="px-3 py-2 text-xs rounded bg-surface-tertiary text-text-secondary border border-border">Generate Plan</button>
            <div className="flex items-center gap-1 border border-border rounded px-1">
              {(['validate_only', 'implement', 'implement_and_validate'] as const).map((m) => (
                <button key={m} onClick={() => setSelectedMode(m)}
                  className={`px-2 py-1 text-[10px] rounded transition-colors ${
                    selectedMode === m ? 'bg-cyan/10 text-cyan' : 'text-text-tertiary'
                  }`}
                >
                  {m === 'validate_only' ? 'Validate' : m === 'implement' ? 'Implement' : 'Full'}
                </button>
              ))}
            </div>
            <button
              onClick={() => onExecute(id, selectedMode, lastPlan?.packet_id === id && lastPlan?.approved ? lastPlan.plan_id : undefined)}
              disabled={executing}
              className={`px-3 py-2 text-xs rounded border border-border ${
                executing ? 'bg-surface-secondary text-text-tertiary cursor-not-allowed' : 'bg-cyan/10 text-cyan'
              }`}
            >
              {executing ? 'Running...' : 'Execute'}
            </button>
          </>
        )}
        {status === 'validating' && (
          <>
            <button onClick={() => onComplete(id, true)}
              className="px-3 py-2 text-xs rounded bg-ok/10 text-ok border border-border">Mark Done</button>
            <button onClick={() => onComplete(id, false)}
              className="px-3 py-2 text-xs rounded bg-danger/10 text-danger border border-border">Mark Failed</button>
          </>
        )}
      </div>

      {/* Execution Plan */}
      {lastPlan && lastPlan.packet_id === id && (
        <PlanSection plan={lastPlan} onApprove={onApprovePlan} />
      )}

      {/* Execution Result */}
      {activeResult && (
        <ExecutionResultSection result={activeResult} />
      )}

      {/* Detail fields */}
      <div className="border border-border rounded p-4 bg-surface-secondary text-xs space-y-3">
        <Field label="ID" value={id} mono />
        <Field label="Intent" value={String(packet.user_intent || '')} />
        <Field label="Desired State" value={String(packet.desired_end_state || '')} />
        <Field label="Domain" value={String(packet.domain || '')} />
        <Field label="Risk" value={String(packet.risk_class || '')} color={RISK_COLOR[String(packet.risk_class || '')]} />
        <Field label="Leverage" value={String(Number(packet.leverage_score || 0).toFixed(2))} />
        {Array.isArray(packet.success_criteria) && packet.success_criteria.length > 0 && (
          <div>
            <span className="text-text-secondary">Success Criteria:</span>
            <ul className="ml-3 mt-1 text-text-primary">{(packet.success_criteria as string[]).map((c, i) => <li key={i}>• {c}</li>)}</ul>
          </div>
        )}
        {Array.isArray(packet.constraints) && packet.constraints.length > 0 && (
          <div>
            <span className="text-text-secondary">Constraints:</span>
            <ul className="ml-3 mt-1 text-text-primary">{(packet.constraints as string[]).map((c, i) => <li key={i}>• {c}</li>)}</ul>
          </div>
        )}
        {Array.isArray(packet.approval_gates) && packet.approval_gates.length > 0 && (
          <div>
            <span className="text-text-secondary">Approval Gates:</span>
            <ul className="ml-3 mt-1 text-warn">{(packet.approval_gates as string[]).map((g, i) => <li key={i}>• {g}</li>)}</ul>
          </div>
        )}
        {Array.isArray(packet.human_required_actions) && (packet.human_required_actions as string[]).length > 0 && (
          <div>
            <span className="text-text-secondary">Human Actions Required:</span>
            <ul className="ml-3 mt-1 text-warn">{(packet.human_required_actions as string[]).map((a, i) => <li key={i}>• {a}</li>)}</ul>
          </div>
        )}
        <Field label="Validation" value={String(packet.validation_plan || 'none')} />
        <Field label="Rollback" value={String(packet.rollback_plan || 'none')} />
        <Field label="Context" value={String(packet.context_summary || '')} />
      </div>

      {/* Execution Records (from packet detail API) */}
      {Array.isArray(packet.execution_records) && (packet.execution_records as ExecutionRecordSummary[]).length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Execution History</h3>
          <div className="space-y-2">
            {(packet.execution_records as ExecutionRecordSummary[]).map((rec) => (
              <div key={rec.record_id} className="border border-border rounded p-3 bg-surface-secondary text-xs space-y-1">
                <div className="flex items-center gap-3">
                  <span className={`font-mono ${rec.success ? 'text-ok' : 'text-danger'}`}>
                    {rec.success ? 'PASSED' : 'FAILED'}
                  </span>
                  <span className="text-text-tertiary">{rec.mode}</span>
                  <span className="text-text-tertiary">{rec.duration_seconds.toFixed(1)}s</span>
                  <span className="text-text-tertiary font-mono text-[10px]">{rec.record_id}</span>
                </div>
                {rec.files_changed.length > 0 && (
                  <div className="text-text-secondary">Files: {rec.files_changed.join(', ')}</div>
                )}
                {rec.commits.length > 0 && (
                  <div className="text-text-secondary">Commits: {rec.commits.join(', ')}</div>
                )}
                {rec.error && <div className="text-danger">{rec.error}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Audit trail */}
      {Array.isArray(packet.audit_trail) && (packet.audit_trail as Array<Record<string, unknown>>).length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Audit Trail</h3>
          <div className="space-y-1">
            {(packet.audit_trail as Array<Record<string, unknown>>).map((entry, i) => (
              <div key={i} className="text-xs text-text-secondary border-l-2 border-border pl-2 py-1">
                <span className="text-cyan">{String(entry.event_type)}</span>
                <span className="text-text-tertiary ml-2">
                  {entry.timestamp ? new Date(Number(entry.timestamp) * 1000).toLocaleString() : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function PlanSection({ plan, onApprove }: { plan: ExecutionPlan; onApprove: (id: string) => void }) {
  return (
    <div className="border border-border rounded p-3 bg-surface-secondary space-y-2">
      <div className="flex items-center gap-3">
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Execution Plan</h3>
        <span className="text-[10px] font-mono text-text-tertiary">{plan.plan_id}</span>
        {plan.approved ? (
          <span className="text-[10px] text-ok font-mono uppercase">approved</span>
        ) : (
          <button onClick={() => onApprove(plan.plan_id)}
            className="px-2 py-1 text-[10px] rounded bg-ok/10 text-ok border border-border">
            Approve Plan
          </button>
        )}
      </div>
      <div className="text-xs space-y-1">
        {plan.objectives.length > 0 && (
          <div>
            <span className="text-text-secondary">Objectives:</span>
            <ul className="ml-3 mt-1 text-text-primary">{plan.objectives.map((o, i) => <li key={i}>• {o}</li>)}</ul>
          </div>
        )}
        {plan.files_expected.length > 0 && (
          <div>
            <span className="text-text-secondary">Expected Files:</span>
            <ul className="ml-3 mt-1 text-text-primary font-mono">{plan.files_expected.map((f, i) => <li key={i}>• {f}</li>)}</ul>
          </div>
        )}
        <Field label="Validation Strategy" value={plan.validation_strategy} />
        <Field label="Rollback Strategy" value={plan.rollback_strategy} />
        <Field label="Risk Assessment" value={plan.risk_assessment} color={RISK_COLOR[plan.risk_assessment]} />
      </div>
    </div>
  )
}

function ExecutionResultSection({ result }: { result: Record<string, unknown> }) {
  const success = Boolean(result.execution_success)
  const mode = String(result.mode || '')
  const agentOutput = String(result.agent_output || '')
  const filesChanged = Array.isArray(result.files_changed) ? result.files_changed as string[] : []
  const diffSummary = String(result.diff_summary || '')
  const commits = Array.isArray(result.commits) ? result.commits as string[] : []
  const validationResults = Array.isArray(result.validation_results) ? result.validation_results as ValidationResult[] : []
  const duration = Number(result.duration_seconds || 0)
  const error = String(result.error || '')
  const needsReview = Boolean(result.needs_review)
  const failureReport = result.failure_report as FailureReport | null

  return (
    <div className={`border rounded p-3 space-y-3 ${success ? 'border-ok/30' : 'border-danger/30'}`}>
      <div className="flex items-center gap-3">
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Execution Result</h3>
        <span className={`text-xs font-mono ${success ? 'text-ok' : 'text-danger'}`}>
          {success ? 'SUCCESS' : 'FAILED'}
        </span>
        <span className="text-[10px] text-text-tertiary">{mode} · {duration.toFixed(1)}s</span>
        {needsReview && <span className="text-[10px] text-warn font-mono uppercase">review required</span>}
      </div>

      {agentOutput && (
        <div>
          <span className="text-[10px] text-text-secondary uppercase">Agent Output</span>
          <pre className="mt-1 p-2 bg-surface rounded text-[11px] text-text-primary whitespace-pre-wrap max-h-40 overflow-y-auto font-mono">
            {agentOutput}
          </pre>
        </div>
      )}

      {filesChanged.length > 0 && (
        <div>
          <span className="text-[10px] text-text-secondary uppercase">Files Changed ({filesChanged.length})</span>
          <div className="mt-1 space-y-0.5">
            {filesChanged.map((f, i) => (
              <div key={i} className="text-xs font-mono text-text-primary">{f}</div>
            ))}
          </div>
        </div>
      )}

      {diffSummary && (
        <div>
          <span className="text-[10px] text-text-secondary uppercase">Diff Summary</span>
          <pre className="mt-1 p-2 bg-surface rounded text-[11px] text-text-primary whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
            {diffSummary}
          </pre>
        </div>
      )}

      {commits.length > 0 && (
        <div>
          <span className="text-[10px] text-text-secondary uppercase">Commits</span>
          <div className="mt-1 space-y-0.5">
            {commits.map((c, i) => (
              <div key={i} className="text-xs font-mono text-cyan">{c}</div>
            ))}
          </div>
        </div>
      )}

      {validationResults.length > 0 && (
        <div>
          <span className="text-[10px] text-text-secondary uppercase">Validation ({validationResults.filter((v) => v.passed).length}/{validationResults.length} passed)</span>
          <div className="mt-1 space-y-1">
            {validationResults.map((v, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${v.passed ? 'bg-ok' : 'bg-danger'}`} />
                <div className="flex-1 min-w-0">
                  <span className="text-text-primary">{v.label}</span>
                  <span className="text-text-tertiary ml-2">{v.duration_seconds.toFixed(1)}s</span>
                  {!v.passed && v.stderr && (
                    <pre className="mt-1 p-1 bg-surface rounded text-[10px] text-danger whitespace-pre-wrap max-h-20 overflow-y-auto">
                      {v.stderr}
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="text-xs text-danger bg-danger/5 p-2 rounded">
          <span className="font-semibold">Error:</span> {error}
        </div>
      )}

      {failureReport && (
        <div className="border border-danger/20 rounded p-2 space-y-1 text-xs">
          <span className="text-[10px] text-danger uppercase font-semibold">Failure Report</span>
          <Field label="Root Cause" value={failureReport.root_cause} />
          <Field label="Failing Command" value={failureReport.failing_command} mono />
          <Field label="Recommended" value={failureReport.recommended_action} />
          <Field label="Retries" value={`${failureReport.retry_count}/${failureReport.max_retries}`} />
        </div>
      )}
    </div>
  )
}

function Field({ label, value, mono, color }: { label: string; value: string; mono?: boolean; color?: string }) {
  if (!value) return null
  return (
    <div>
      <span className="text-text-secondary">{label}:</span>{' '}
      <span className={`text-text-primary ${mono ? 'font-mono' : ''} ${color || ''}`}>{value}</span>
    </div>
  )
}


// ── Phase 3: Empire components ──────────────────────────────────────

function RoutingResultBanner({ routing, onDismiss }: { routing: RoutingResultData; onDismiss: () => void }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <span className="text-[10px] text-cyan font-semibold uppercase">Routed</span>
        <span className={`px-1.5 py-0.5 text-[10px] rounded ${RISK_COLOR[routing.risk_level] ?? 'text-text-secondary'} bg-surface border border-border`}>
          {routing.risk_level} risk
        </span>
        <span className="text-[10px] text-text-secondary">{routing.domain_label}</span>
        <span className="text-[10px] text-text-secondary/60">{routing.scope}</span>
        {routing.urgency !== 'normal' && (
          <span className={`text-[10px] ${routing.urgency === 'urgent' ? 'text-danger' : 'text-warn'}`}>
            {routing.urgency}
          </span>
        )}
        <div className="flex-1" />
        <button onClick={onDismiss} className="text-[10px] text-text-secondary hover:text-text-primary">dismiss</button>
      </div>

      {routing.work_packets.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {routing.work_packets.map((wp, i) => (
            <span key={i} className="px-2 py-0.5 text-[10px] rounded bg-surface border border-border text-text-primary">
              {String(wp.title || wp.user_intent || `Packet ${i + 1}`).slice(0, 60)}
            </span>
          ))}
        </div>
      )}

      {routing.suggested_agents.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-secondary">Agents:</span>
          {routing.suggested_agents.map((a, i) => (
            <span key={i} className="text-[10px] text-cyan">{a}</span>
          ))}
        </div>
      )}

      {routing.proof_requirements.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-secondary">Proof:</span>
          {routing.proof_requirements.map((p, i) => (
            <span key={i} className="text-[10px] text-text-secondary/80">{p.proof_type}</span>
          ))}
        </div>
      )}

      {routing.missing_context.length > 0 && (
        <div className="text-[10px] text-warn">
          {routing.missing_context.map((m, i) => (
            <div key={i}>{m}</div>
          ))}
        </div>
      )}

      {routing.next_action && (
        <div className="text-[10px] text-text-secondary">
          Next: <span className="text-text-primary">{routing.next_action.replace(/_/g, ' ')}</span>
        </div>
      )}
    </div>
  )
}
