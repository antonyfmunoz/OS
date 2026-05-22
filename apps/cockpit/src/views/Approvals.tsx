import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { relativeTime } from '../lib/time.ts'
import type { ApprovalItem } from '../types/domain.ts'

type TabFilter = ApprovalItem['status'] | 'all'

const TABS: { id: TabFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'pending', label: 'Pending' },
  { id: 'approved', label: 'Approved' },
  { id: 'denied', label: 'Denied' },
]

const RISK_COLOR: Record<ApprovalItem['riskLevel'], string> = {
  low: 'wv-badge-ok',
  medium: 'wv-badge-warn',
  high: 'wv-badge-danger',
  critical: 'wv-badge-violet',
}

const RISK_SORT_WEIGHT: Record<ApprovalItem['riskLevel'], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

const STATUS_BADGE: Record<ApprovalItem['status'], string> = {
  pending: 'wv-badge-warn',
  approved: 'wv-badge-ok',
  denied: 'wv-badge-danger',
}

function StatsBar({ approvals }: { approvals: ApprovalItem[] }) {
  const pending = approvals.filter((a) => a.status === 'pending').length
  const approved = approvals.filter((a) => a.status === 'approved').length
  const denied = approvals.filter((a) => a.status === 'denied').length
  const highRisk = approvals.filter(
    (a) => a.status === 'pending' && (a.riskLevel === 'high' || a.riskLevel === 'critical'),
  ).length

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-warn">{pending}</div>
        <div className="wv-label mt-1">PENDING</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-ok">{approved}</div>
        <div className="wv-label mt-1">APPROVED</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className="wv-metric text-danger">{denied}</div>
        <div className="wv-label mt-1">DENIED</div>
      </div>
      <div className="wv-card p-3 text-center">
        <div className={clsx('wv-metric', highRisk > 0 ? 'text-danger' : 'text-text-tertiary')}>
          {highRisk}
        </div>
        <div className="wv-label mt-1">HIGH/CRIT PENDING</div>
      </div>
    </div>
  )
}

function ApprovalCard({
  item,
  selected,
  onClick,
}: {
  item: ApprovalItem
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left wv-card-raised p-4 transition-colors',
        selected && 'ring-1 ring-cyan',
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[12px] text-text-primary font-mono">{item.title}</span>
        <div className="flex items-center gap-2">
          <span className={clsx('wv-badge', RISK_COLOR[item.riskLevel])}>{item.riskLevel}</span>
          <span className={clsx('wv-badge', STATUS_BADGE[item.status])}>{item.status}</span>
        </div>
      </div>
      <div className="text-[11px] text-text-secondary mb-2">{item.description}</div>
      <div className="flex items-center gap-3 text-[10px] text-text-tertiary">
        <span>Agent: {item.agent}</span>
        <span>{relativeTime(item.createdAt)}</span>
      </div>
    </button>
  )
}

function DetailPanel({
  item,
  onApprove,
  onDeny,
  onClose,
}: {
  item: ApprovalItem
  onApprove: () => void
  onDeny: (rationale: string) => void
  onClose: () => void
}) {
  const [rationale, setRationale] = useState('')
  const [showDenyInput, setShowDenyInput] = useState(false)

  const handleDeny = () => {
    onDeny(rationale || 'Denied without rationale')
    setRationale('')
    setShowDenyInput(false)
  }

  return (
    <div className="w-96 border-l border-border flex flex-col bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <span className="wv-label">APPROVAL DETAIL</span>
        <button
          onClick={onClose}
          className="text-text-tertiary hover:text-text-primary text-[14px] transition-colors"
        >
          ✕
        </button>
      </div>
      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div>
          <div className="wv-label mb-1">TITLE</div>
          <div className="text-[12px] text-text-primary">{item.title}</div>
        </div>
        <div>
          <div className="wv-label mb-1">DESCRIPTION</div>
          <div className="text-[11px] text-text-secondary leading-relaxed">{item.description}</div>
        </div>
        <div className="flex gap-4">
          <div>
            <div className="wv-label mb-1">RISK</div>
            <span className={clsx('wv-badge', RISK_COLOR[item.riskLevel])}>{item.riskLevel}</span>
          </div>
          <div>
            <div className="wv-label mb-1">STATUS</div>
            <span className={clsx('wv-badge', STATUS_BADGE[item.status])}>{item.status}</span>
          </div>
        </div>
        <div>
          <div className="wv-label mb-1">AGENT</div>
          <div className="text-[11px] text-cyan">{item.agent}</div>
        </div>
        <div>
          <div className="wv-label mb-1">CREATED</div>
          <div className="text-[11px] text-text-secondary">{new Date(item.createdAt).toLocaleString()}</div>
        </div>

        {item.status === 'pending' && (
          <div className="border-t border-border pt-4 space-y-3">
            <div className="wv-label">ACTIONS</div>

            {!showDenyInput && (
              <div className="flex gap-2">
                <button
                  onClick={onApprove}
                  className="flex-1 px-4 py-2 text-[11px] font-mono uppercase tracking-wider bg-ok/10 text-ok border border-ok-dim hover:bg-ok/20 transition-colors"
                >
                  Approve
                </button>
                <button
                  onClick={() => setShowDenyInput(true)}
                  className="flex-1 px-4 py-2 text-[11px] font-mono uppercase tracking-wider bg-danger/10 text-danger border border-danger-dim hover:bg-danger/20 transition-colors"
                >
                  Deny
                </button>
              </div>
            )}

            {showDenyInput && (
              <div className="space-y-2">
                <textarea
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  placeholder="Reason for denial (optional)..."
                  className="w-full bg-surface border border-border text-text-primary text-[11px] font-mono p-2 h-20 resize-none placeholder:text-text-tertiary focus:border-cyan-dim focus:outline-none"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleDeny}
                    className="flex-1 px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider bg-danger/10 text-danger border border-danger-dim hover:bg-danger/20 transition-colors"
                  >
                    Confirm Deny
                  </button>
                  <button
                    onClick={() => setShowDenyInput(false)}
                    className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-text-tertiary border border-border hover:border-border-active transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export function Approvals() {
  const { approvals, updateApproval } = useCockpitStore()
  const [tab, setTab] = useState<TabFilter>('pending')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const items = tab === 'all' ? approvals : approvals.filter((a) => a.status === tab)
    return [...items].sort((a, b) => {
      if (a.status === 'pending' && b.status !== 'pending') return -1
      if (b.status === 'pending' && a.status !== 'pending') return 1
      return RISK_SORT_WEIGHT[a.riskLevel] - RISK_SORT_WEIGHT[b.riskLevel]
    })
  }, [approvals, tab])

  const selectedItem = approvals.find((a) => a.id === selectedId) ?? null
  const pendingCount = approvals.filter((a) => a.status === 'pending').length

  const handleApprove = async () => {
    if (selectedId) {
      const { api } = await import('../api/client.ts')
      await api.approveItem(selectedId)
      updateApproval(selectedId, 'approved')
      setSelectedId(null)
      useCockpitStore.getState().fetchAll()
    }
  }

  const handleDeny = async (_rationale: string) => {
    if (selectedId) {
      const { api } = await import('../api/client.ts')
      await api.denyItem(selectedId, _rationale)
      updateApproval(selectedId, 'denied')
      setSelectedId(null)
      useCockpitStore.getState().fetchAll()
    }
  }

  return (
    <div className="h-full flex flex-col p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">
          Approvals
        </h1>
        {pendingCount > 0 && (
          <span className="wv-badge wv-badge-warn">{pendingCount} awaiting decision</span>
        )}
      </div>

      <StatsBar approvals={approvals} />

      {/* Tab bar */}
      <div className="flex gap-1 mb-4">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={clsx(
              'px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider border transition-colors',
              tab === t.id
                ? 'text-cyan bg-cyan-glow border-cyan-dim'
                : 'text-text-tertiary border-border hover:text-text-secondary hover:border-border-active',
            )}
          >
            {t.label}
            {t.id === 'pending' && pendingCount > 0 && (
              <span className="ml-1.5 text-warn">({pendingCount})</span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 flex min-h-0">
        {/* Approval list */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-2">
          {filtered.length === 0 && (
            <div className="text-center text-text-tertiary text-[11px] py-12">
              No items in this category
            </div>
          )}
          {filtered.map((item) => (
            <ApprovalCard
              key={item.id}
              item={item}
              selected={item.id === selectedId}
              onClick={() => setSelectedId(item.id === selectedId ? null : item.id)}
            />
          ))}
        </div>

        {/* Detail panel */}
        {selectedItem && (
          <DetailPanel
            item={selectedItem}
            onApprove={handleApprove}
            onDeny={handleDeny}
            onClose={() => setSelectedId(null)}
          />
        )}
      </div>
    </div>
  )
}
