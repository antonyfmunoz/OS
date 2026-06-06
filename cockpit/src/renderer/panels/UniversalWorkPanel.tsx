import { useEffect, useState, useCallback } from 'react'
import { fetchApi } from '../api/client'
import { ConnectionBanner } from '../components/ConnectionBanner'
import { usePolling } from '../hooks/usePolling'
import { useOperatorLoopStore } from '../stores/operatorLoopStore'

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

  const submitIntent = useOperatorLoopStore((s) => s.submitIntent)
  const approvePacket = useOperatorLoopStore((s) => s.approvePacket)
  const rejectPacket = useOperatorLoopStore((s) => s.rejectPacket)
  const executePacket = useOperatorLoopStore((s) => s.executePacket)
  const completePacket = useOperatorLoopStore((s) => s.completePacket)

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

  const selectPacket = useCallback(async (id: string) => {
    const detail = await fetchApi<Record<string, unknown>>(`/organism/universal-work/packets/${id}`).catch(() => null)
    setSelected(detail)
    setViewMode('detail')
  }, [])

  const handleCreate = async () => {
    if (!intentText.trim()) return
    const pkt = await submitIntent(intentText, desiredEndState)
    if (pkt) {
      setIntentText('')
      setDesiredEndState('')
      setShowCreate(false)
      refresh()
    }
  }

  const handleApprove = async (id: string) => {
    await approvePacket(id)
    refresh()
    if (selected && String(selected.packet_id) === id) {
      selectPacket(id)
    }
  }

  const handleReject = async (id: string) => {
    await rejectPacket(id)
    refresh()
  }

  const handleExecute = async (id: string) => {
    await executePacket(id)
    refresh()
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
        <h2 className="text-sm font-semibold text-text-primary">Work Packets</h2>
        <span className="text-xs text-text-secondary">{summary.total_packets} total</span>
        <div className="flex-1" />

        {/* View mode tabs */}
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

      {/* Create form */}
      {showCreate && (
        <div className="px-4 py-3 border-b border-border bg-surface-secondary space-y-2">
          <input value={intentText} onChange={(e) => setIntentText(e.target.value)}
            placeholder="What do you want UMH to do?"
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
            >Submit Intent</button>
            <button onClick={() => setShowCreate(false)}
              className="px-3 py-1 text-xs rounded text-text-secondary border border-border"
            >Cancel</button>
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 overflow-auto">
        {viewMode === 'kanban' && (
          <KanbanView packets={packets} onSelect={selectPacket}
            onApprove={handleApprove} onReject={handleReject}
            onExecute={handleExecute} onComplete={handleComplete} />
        )}
        {viewMode === 'table' && (
          <TableView packets={packets} onSelect={selectPacket}
            onApprove={handleApprove} onReject={handleReject}
            onExecute={handleExecute} onComplete={handleComplete} />
        )}
        {viewMode === 'detail' && selected && (
          <DetailView packet={selected} onBack={() => setViewMode('kanban')}
            onApprove={handleApprove} onReject={handleReject}
            onExecute={handleExecute} onComplete={handleComplete} />
        )}
      </div>
    </div>
  )
}

function KanbanView({ packets, onSelect, onApprove, onReject, onExecute, onComplete }: {
  packets: PacketSafe[]
  onSelect: (id: string) => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
  onExecute: (id: string) => void
  onComplete: (id: string, success: boolean) => void
}) {
  return (
    <div className="flex gap-2 p-3 h-full overflow-x-auto">
      {KANBAN_COLUMNS.map((col) => {
        const colPackets = packets.filter((p) => col.statuses.includes(p.status))
        return (
          <div key={col.key} className="flex-shrink-0 w-56 flex flex-col">
            <div className="flex items-center gap-2 px-2 py-2 mb-1">
              <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">{col.label}</span>
              <span className="text-xs text-text-tertiary">{colPackets.length}</span>
            </div>
            <div className="flex-1 overflow-y-auto space-y-1.5">
              {colPackets.map((pkt) => (
                <KanbanCard key={pkt.packet_id} packet={pkt} onClick={() => onSelect(pkt.packet_id)}
                  onApprove={onApprove} onReject={onReject} onExecute={onExecute} onComplete={onComplete} />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function KanbanCard({ packet, onClick, onApprove, onReject, onExecute, onComplete }: {
  packet: PacketSafe
  onClick: () => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
  onExecute: (id: string) => void
  onComplete: (id: string, success: boolean) => void
}) {
  return (
    <div className="border border-border rounded p-2 bg-surface-secondary cursor-pointer hover:border-cyan transition-colors"
         onClick={onClick}>
      <p className="text-xs font-medium text-text-primary truncate mb-1">{packet.title}</p>
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-[10px] font-mono ${RISK_COLOR[packet.risk_class]}`}>{packet.risk_class}</span>
        <span className="text-[10px] text-text-tertiary">{packet.domain}</span>
      </div>
      {packet.approval_gates.length > 0 && (
        <span className="text-[10px] text-warn">approval required</span>
      )}

      {/* Inline controls */}
      <div className="flex gap-1 mt-2" onClick={(e) => e.stopPropagation()}>
        {packet.status === 'approval_pending' && (
          <>
            <button onClick={() => onApprove(packet.packet_id)}
              className="px-2 py-1 text-[10px] rounded bg-ok/10 text-ok border border-border">approve</button>
            <button onClick={() => onReject(packet.packet_id)}
              className="px-2 py-1 text-[10px] rounded bg-danger/10 text-danger border border-border">reject</button>
          </>
        )}
        {(packet.status === 'approved' || (packet.status === 'classified' && packet.approval_gates.length === 0)) && (
          <button onClick={() => onExecute(packet.packet_id)}
            className="px-2 py-1 text-[10px] rounded bg-cyan/10 text-cyan border border-border">execute</button>
        )}
        {packet.status === 'executing' && (
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
  onExecute: (id: string) => void
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
                      <button onClick={() => onExecute(pkt.packet_id)}
                        className="px-2 py-1 text-[10px] rounded text-cyan border border-border">▶</button>
                    )}
                    {pkt.status === 'executing' && (
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

function DetailView({ packet, onBack, onApprove, onReject, onExecute, onComplete }: {
  packet: Record<string, unknown>
  onBack: () => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
  onExecute: (id: string) => void
  onComplete: (id: string, success: boolean) => void
}) {
  const id = String(packet.packet_id || '')
  const status = String(packet.status || '')

  return (
    <div className="p-4 space-y-4 max-w-3xl">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="text-xs text-text-secondary hover:text-text-primary">← Back</button>
        <h2 className="text-sm font-semibold text-text-primary">{String(packet.title || 'Untitled')}</h2>
        <span className={`text-xs font-mono ${STATUS_COLOR[status]}`}>{status}</span>
      </div>

      {/* Action bar */}
      <div className="flex gap-2">
        {status === 'approval_pending' && (
          <>
            <button onClick={() => onApprove(id)}
              className="px-3 py-2 text-xs rounded bg-ok/10 text-ok border border-border">Approve</button>
            <button onClick={() => onReject(id)}
              className="px-3 py-2 text-xs rounded bg-danger/10 text-danger border border-border">Reject</button>
          </>
        )}
        {(status === 'approved' || (status === 'classified' && !Array.isArray(packet.approval_gates) || (Array.isArray(packet.approval_gates) && packet.approval_gates.length === 0))) && (
          <button onClick={() => onExecute(id)}
            className="px-3 py-2 text-xs rounded bg-cyan/10 text-cyan border border-border">Execute</button>
        )}
        {status === 'executing' && (
          <>
            <button onClick={() => onComplete(id, true)}
              className="px-3 py-2 text-xs rounded bg-ok/10 text-ok border border-border">Mark Done</button>
            <button onClick={() => onComplete(id, false)}
              className="px-3 py-2 text-xs rounded bg-danger/10 text-danger border border-border">Mark Failed</button>
          </>
        )}
      </div>

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

function Field({ label, value, mono, color }: { label: string; value: string; mono?: boolean; color?: string }) {
  if (!value) return null
  return (
    <div>
      <span className="text-text-secondary">{label}:</span>{' '}
      <span className={`text-text-primary ${mono ? 'font-mono' : ''} ${color || ''}`}>{value}</span>
    </div>
  )
}

function StatCard({ label, value, color = 'text-text-primary' }: { label: string; value: number; color?: string }) {
  return (
    <div className="border border-border rounded px-3 py-2 bg-surface-secondary">
      <div className="text-xs text-text-secondary">{label}</div>
      <div className={`text-lg font-mono ${color}`}>{value}</div>
    </div>
  )
}
