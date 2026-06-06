export interface ActionItem {
  id: string
  type: 'approval' | 'blocked' | 'failed' | 'stale' | 'throttle' | 'capture'
  label: string
  severity: 'info' | 'warn' | 'danger'
  onClick?: () => void
}

const SEVERITY_COLOR: Record<string, string> = {
  info: 'var(--color-cyan)',
  warn: 'var(--color-warn)',
  danger: 'var(--color-danger)',
}

const TYPE_ICON: Record<string, string> = {
  approval: '!',
  blocked: '#',
  failed: 'x',
  stale: '~',
  throttle: '^',
  capture: '>',
}

interface ActionRequiredProps {
  items: ActionItem[]
  loading?: boolean
}

export function ActionRequired({ items, loading }: ActionRequiredProps) {
  if (loading) return null

  if (items.length === 0) {
    return null
  }

  return (
    <div className="flex flex-col gap-1">
      <span className="wv-label mb-1">Action Required</span>
      {items.map((item) => (
        <div
          key={item.id}
          onClick={item.onClick}
          className="flex items-center gap-2 px-3 py-2 rounded-md transition-colors"
          style={{
            background: 'var(--color-surface-raised)',
            border: '1px solid var(--color-border)',
            cursor: item.onClick ? 'pointer' : 'default',
          }}
        >
          <span
            data-severity={item.severity}
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: SEVERITY_COLOR[item.severity] }}
          />
          <span className="text-xs font-mono" style={{ marginRight: 3 }}>
            {TYPE_ICON[item.type] || '-'}
          </span>
          <span
            className="text-xs flex-1"
            style={{ color: 'var(--color-text-primary)' }}
          >
            {item.label}
          </span>
        </div>
      ))}
    </div>
  )
}

export function buildActionItems(
  summary: {
    what_needs_approval?: { count?: number; items?: { id: string; title: string; risk_level: string }[] }
    what_is_blocked?: { count?: number; items?: { id: string; title: string; blockers: string[] }[] }
    what_failed?: { recent_failed?: number; latest?: string }
  } | null,
  callbacks?: {
    onApprovalClick?: () => void
    onBlockedClick?: () => void
  }
): ActionItem[] {
  if (!summary) return []
  const items: ActionItem[] = []

  const approvalCount = summary.what_needs_approval?.count ?? summary.what_needs_approval?.items?.length ?? 0
  if (approvalCount > 0) {
    items.push({
      id: 'approvals',
      type: 'approval',
      label: `${approvalCount} approval${approvalCount > 1 ? 's' : ''} waiting`,
      severity: 'warn',
      onClick: callbacks?.onApprovalClick,
    })
  }

  const blockedCount = summary.what_is_blocked?.count ?? summary.what_is_blocked?.items?.length ?? 0
  if (blockedCount > 0) {
    items.push({
      id: 'blocked',
      type: 'blocked',
      label: `${blockedCount} blocked packet${blockedCount > 1 ? 's' : ''}`,
      severity: 'danger',
      onClick: callbacks?.onBlockedClick,
    })
  }

  const failedCount = summary.what_failed?.recent_failed ?? 0
  if (failedCount > 0) {
    items.push({
      id: 'failed',
      type: 'failed',
      label: `${failedCount} recent failure${failedCount > 1 ? 's' : ''}`,
      severity: 'danger',
    })
  }

  return items
}
