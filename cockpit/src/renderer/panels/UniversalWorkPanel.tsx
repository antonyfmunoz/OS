import { useEffect, useState, useCallback } from 'react'
import { fetchApi } from '../api/client'
import { ConnectionBanner } from '../components/ConnectionBanner'
import { usePolling } from '../hooks/usePolling'

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

export function UniversalWorkPanel() {
  const [summary, setSummary] = useState<QueueSummary | null>(null)
  const [packets, setPackets] = useState<PacketSafe[]>([])
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null)

  const refresh = useCallback(async () => {
    const [s, p] = await Promise.all([
      fetchApi<QueueSummary>('/organism/universal-work/summary').catch(() => null),
      fetchApi<PacketSafe[]>('/organism/universal-work/packets?limit=30').catch(() => []),
    ])
    if (s) setSummary(s)
    setPackets(p)
  }, [])

  useEffect(() => { refresh() }, [refresh])
  usePolling(refresh, 10000)

  const selectPacket = useCallback(async (id: string) => {
    const detail = await fetchApi<Record<string, unknown>>(`/organism/universal-work/packets/${id}`).catch(() => null)
    setSelected(detail)
  }, [])

  if (!summary) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <ConnectionBanner />
        <div className="flex items-center justify-center flex-1">
          <span className="text-text-secondary text-sm">Loading universal work queue...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />

      <div className="flex items-center gap-4 px-4 py-2 flex-shrink-0 border-b border-border">
        <h2 className="text-sm font-semibold text-text-primary">Universal Work Queue</h2>
        <span className="text-xs text-text-secondary">{summary.total_packets} packets</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">

        {/* Summary Stats */}
        <section>
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Queue Summary</h3>
          <div className="grid grid-cols-4 gap-2">
            <StatCard label="Total" value={summary.total_packets} />
            <StatCard label="Active" value={summary.active} color="text-cyan" />
            <StatCard label="Human" value={summary.human_required} color="text-warn" />
            <StatCard label="Approval" value={summary.approval_required} color="text-warn" />
            <StatCard label="Blocked" value={summary.blocked} color="text-danger" />
            <StatCard label="Done" value={summary.completed} color="text-ok" />
          </div>
        </section>

        {/* Domain Breakdown */}
        {Object.keys(summary.by_domain).length > 0 && (
          <section>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">By Domain</h3>
            <div className="flex flex-wrap gap-2">
              {Object.entries(summary.by_domain).map(([domain, count]) => (
                <span key={domain} className="text-xs border border-border rounded px-2 py-1 bg-surface-secondary">
                  {domain}: <span className="text-cyan">{count}</span>
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Next Best */}
        {summary.next_best && (
          <section>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Next Best Packet</h3>
            <div className="border border-border rounded p-3 bg-surface-secondary cursor-pointer hover:border-cyan"
                 onClick={() => selectPacket(summary.next_best!.packet_id)}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-text-primary">{summary.next_best.title}</span>
                <span className="text-xs text-cyan">{summary.next_best.leverage_score.toFixed(2)}</span>
              </div>
              <div className="text-xs text-text-secondary mb-1 truncate">{summary.next_best.user_intent}</div>
              <div className="flex gap-3 text-xs text-text-secondary">
                <span>{summary.next_best.domain}</span>
                <span className={RISK_COLOR[summary.next_best.risk_class]}>{summary.next_best.risk_class}</span>
                <span className={STATUS_COLOR[summary.next_best.status]}>{summary.next_best.status}</span>
                {summary.next_best.linked_roadmap_phase && <span>Phase {summary.next_best.linked_roadmap_phase}</span>}
              </div>
            </div>
          </section>
        )}

        {/* Packets Table */}
        <section>
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Work Packets</h3>
          <div className="border border-border rounded overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-surface-secondary text-text-secondary">
                  <th className="px-2 py-1 text-left">Status</th>
                  <th className="px-2 py-1 text-left">Title</th>
                  <th className="px-2 py-1 text-left">Domain</th>
                  <th className="px-2 py-1 text-right">Leverage</th>
                  <th className="px-2 py-1 text-left">Risk</th>
                  <th className="px-2 py-1 text-left">Topology</th>
                  <th className="px-2 py-1 text-center">Human</th>
                </tr>
              </thead>
              <tbody>
                {packets.map((pkt) => (
                  <tr key={pkt.packet_id}
                      className="border-t border-border hover:bg-surface-secondary cursor-pointer"
                      onClick={() => selectPacket(pkt.packet_id)}>
                    <td className={`px-2 py-1 ${STATUS_COLOR[pkt.status] || ''}`}>{pkt.status}</td>
                    <td className="px-2 py-1 text-text-primary truncate max-w-[180px]">{pkt.title}</td>
                    <td className="px-2 py-1 text-text-secondary">{pkt.domain}</td>
                    <td className="px-2 py-1 text-right text-cyan">{pkt.leverage_score.toFixed(2)}</td>
                    <td className={`px-2 py-1 ${RISK_COLOR[pkt.risk_class] || ''}`}>{pkt.risk_class}</td>
                    <td className="px-2 py-1 text-text-secondary">{pkt.delegation_topology_id ? 'yes' : '-'}</td>
                    <td className="px-2 py-1 text-center">{pkt.human_required_actions.length > 0 ? 'Y' : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Packet Detail */}
        {selected && (
          <section>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
              Packet Detail
              <button className="ml-2 text-text-secondary hover:text-text-primary" onClick={() => setSelected(null)}>x</button>
            </h3>
            <div className="border border-border rounded p-3 bg-surface-secondary text-xs space-y-2">
              <div><span className="text-text-secondary">ID:</span> <span className="text-cyan font-mono">{String(selected.packet_id || '')}</span></div>
              <div><span className="text-text-secondary">Intent:</span> <span className="text-text-primary">{String(selected.user_intent || '')}</span></div>
              <div><span className="text-text-secondary">Desired State:</span> <span className="text-text-primary">{String(selected.desired_end_state || '')}</span></div>
              <div><span className="text-text-secondary">Context:</span> <span className="text-text-primary">{String(selected.context_summary || '')}</span></div>
              {Array.isArray(selected.success_criteria) && selected.success_criteria.length > 0 && (
                <div>
                  <span className="text-text-secondary">Success Criteria:</span>
                  <ul className="ml-3 text-text-primary">{(selected.success_criteria as string[]).map((c, i) => <li key={i}>- {c}</li>)}</ul>
                </div>
              )}
              {Array.isArray(selected.constraints) && selected.constraints.length > 0 && (
                <div>
                  <span className="text-text-secondary">Constraints:</span>
                  <ul className="ml-3 text-text-primary">{(selected.constraints as string[]).map((c, i) => <li key={i}>- {c}</li>)}</ul>
                </div>
              )}
              {Array.isArray(selected.workcells) && selected.workcells.length > 0 && (
                <div><span className="text-text-secondary">Workcells:</span> <span className="text-cyan">{(selected.workcells as string[]).join(', ')}</span></div>
              )}
              {Array.isArray(selected.human_required_actions) && selected.human_required_actions.length > 0 && (
                <div>
                  <span className="text-text-secondary">Human Actions:</span>
                  <ul className="ml-3 text-warn">{(selected.human_required_actions as string[]).map((a, i) => <li key={i}>- {a}</li>)}</ul>
                </div>
              )}
              <div><span className="text-text-secondary">Validation:</span> <span className="text-text-primary">{String(selected.validation_plan || 'none')}</span></div>
              <div><span className="text-text-secondary">Rollback:</span> <span className="text-text-primary">{String(selected.rollback_plan || 'none')}</span></div>
              <div><span className="text-text-secondary">Propagation:</span> <span className="text-text-primary">{String(selected.propagation_plan || 'none')}</span></div>
            </div>
          </section>
        )}
      </div>
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
