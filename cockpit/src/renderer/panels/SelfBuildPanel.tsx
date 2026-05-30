import { useEffect, useState, useCallback } from 'react'
import { fetchApi } from '../api/client'
import { ConnectionBanner } from '../components/ConnectionBanner'
import { usePolling } from '../hooks/usePolling'

interface QueueSummary {
  total_items: number
  status_counts: Record<string, number>
  risk_counts: Record<string, number>
  source_counts: Record<string, number>
  ready_for_approval: number
  active_work: number
  blocked: number
  production_verified: number
  next_best: WorkItemSafe | null
}

interface WorkItemSafe {
  work_item_id: string
  title: string
  description: string
  source_type: string
  risk_class: string
  promotion_class: string
  weighted_score: number
  status: string
  status_reason: string
  roadmap_phase: string
  blocked_reasons: string[]
  created_at: number
  updated_at: number
}

interface RoadmapSummary {
  total_phases: number
  status_counts: Record<string, number>
  phases: {
    phase_id: string
    title: string
    status: string
    work_items: number
    unlocks: string[]
  }[]
}

const STATUS_COLOR: Record<string, string> = {
  discovered: 'text-text-secondary',
  ranked: 'text-cyan',
  triaged: 'text-cyan',
  ready_for_approval: 'text-warn',
  approval_pending: 'text-warn',
  approved: 'text-ok',
  rejected: 'text-danger',
  blocked: 'text-danger',
  sandbox_ready: 'text-cyan',
  sandbox_running: 'text-cyan',
  sandbox_complete: 'text-ok',
  pr_created: 'text-cyan',
  pr_review: 'text-warn',
  merged: 'text-ok',
  production_verification_pending: 'text-warn',
  production_verified: 'text-ok',
  resolved: 'text-text-secondary',
  failed: 'text-danger',
  superseded: 'text-text-secondary',
  archived: 'text-text-secondary',
}

const RISK_COLOR: Record<string, string> = {
  low: 'text-ok',
  medium: 'text-warn',
  high: 'text-danger',
}

const PHASE_STATUS_COLOR: Record<string, string> = {
  complete: 'text-ok',
  active: 'text-cyan',
  planned: 'text-text-secondary',
  north_star: 'text-warn',
}

export function SelfBuildPanel() {
  const [summary, setSummary] = useState<QueueSummary | null>(null)
  const [items, setItems] = useState<WorkItemSafe[]>([])
  const [roadmap, setRoadmap] = useState<RoadmapSummary | null>(null)
  const [blocked, setBlocked] = useState<WorkItemSafe[]>([])

  const refresh = useCallback(async () => {
    const [s, i, r, b] = await Promise.all([
      fetchApi<QueueSummary>('/organism/self-build/summary').catch(() => null),
      fetchApi<WorkItemSafe[]>('/organism/self-build/items?limit=20').catch(() => []),
      fetchApi<RoadmapSummary>('/organism/roadmap').catch(() => null),
      fetchApi<WorkItemSafe[]>('/organism/self-build/blocked').catch(() => []),
    ])
    if (s) setSummary(s)
    setItems(i)
    if (r) setRoadmap(r)
    setBlocked(b)
  }, [])

  useEffect(() => { refresh() }, [refresh])
  usePolling(refresh, 10000)

  if (!summary) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <ConnectionBanner />
        <div className="flex items-center justify-center flex-1">
          <span className="text-text-secondary text-sm">Loading self-build queue…</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />

      {/* Header */}
      <div className="flex items-center gap-4 px-4 py-2 flex-shrink-0 border-b border-border">
        <h2 className="text-sm font-semibold text-text-primary">Self-Build Engineering Queue</h2>
        <span className="text-xs text-text-secondary">{summary.total_items} items</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">

        {/* Queue Summary */}
        <section>
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Queue Summary</h3>
          <div className="grid grid-cols-4 gap-2">
            <StatCard label="Total" value={summary.total_items} />
            <StatCard label="Ready" value={summary.ready_for_approval} color="text-warn" />
            <StatCard label="Active" value={summary.active_work} color="text-cyan" />
            <StatCard label="Blocked" value={summary.blocked} color="text-danger" />
            <StatCard label="Verified" value={summary.production_verified} color="text-ok" />
            {Object.entries(summary.risk_counts).map(([risk, count]) => (
              <StatCard key={risk} label={risk} value={count} color={RISK_COLOR[risk]} />
            ))}
          </div>
        </section>

        {/* Next Best Work */}
        {summary.next_best && (
          <section>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Next Best Work</h3>
            <div className="border border-border rounded p-3 bg-surface-secondary">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-text-primary">{summary.next_best.title}</span>
                <span className="text-xs text-cyan">{summary.next_best.weighted_score.toFixed(4)}</span>
              </div>
              <div className="flex gap-3 text-xs text-text-secondary">
                <span>Phase {summary.next_best.roadmap_phase || '—'}</span>
                <span className={RISK_COLOR[summary.next_best.risk_class] || ''}>{summary.next_best.risk_class}</span>
                <span className={STATUS_COLOR[summary.next_best.status] || ''}>{summary.next_best.status}</span>
                <span>{summary.next_best.source_type}</span>
              </div>
            </div>
          </section>
        )}

        {/* Work Items Table */}
        <section>
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Work Items</h3>
          <div className="border border-border rounded overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-surface-secondary text-text-secondary">
                  <th className="px-2 py-1 text-left">Status</th>
                  <th className="px-2 py-1 text-left">Title</th>
                  <th className="px-2 py-1 text-right">Score</th>
                  <th className="px-2 py-1 text-left">Risk</th>
                  <th className="px-2 py-1 text-left">Source</th>
                  <th className="px-2 py-1 text-left">Phase</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.work_item_id} className="border-t border-border hover:bg-surface-secondary">
                    <td className={`px-2 py-1 ${STATUS_COLOR[item.status] || ''}`}>{item.status}</td>
                    <td className="px-2 py-1 text-text-primary truncate max-w-[200px]">{item.title}</td>
                    <td className="px-2 py-1 text-right text-cyan">{item.weighted_score.toFixed(3)}</td>
                    <td className={`px-2 py-1 ${RISK_COLOR[item.risk_class] || ''}`}>{item.risk_class}</td>
                    <td className="px-2 py-1 text-text-secondary">{item.source_type.replace(/_/g, ' ')}</td>
                    <td className="px-2 py-1 text-text-secondary">{item.roadmap_phase || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Blocked Work */}
        {blocked.length > 0 && (
          <section>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Blocked ({blocked.length})</h3>
            <div className="space-y-1">
              {blocked.map((item) => (
                <div key={item.work_item_id} className="border border-border rounded p-2 bg-surface-secondary">
                  <span className="text-xs text-text-primary">{item.title}</span>
                  {item.blocked_reasons.length > 0 && (
                    <div className="text-xs text-danger mt-1">
                      {item.blocked_reasons.join('; ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Roadmap */}
        {roadmap && (
          <section>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Roadmap ({roadmap.total_phases} phases)</h3>
            <div className="space-y-1">
              {roadmap.phases.map((phase) => (
                <div key={phase.phase_id} className="flex items-center justify-between border border-border rounded px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-mono ${PHASE_STATUS_COLOR[phase.status] || ''}`}>{phase.phase_id}</span>
                    <span className="text-xs text-text-primary">{phase.title}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs ${PHASE_STATUS_COLOR[phase.status] || ''}`}>{phase.status}</span>
                    <span className="text-xs text-text-secondary">{phase.work_items} items</span>
                  </div>
                </div>
              ))}
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
