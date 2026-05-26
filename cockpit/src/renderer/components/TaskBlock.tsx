interface TaskBlockProps {
  id: string
  title: string
  status: 'pending' | 'in_progress' | 'completed' | 'blocked'
  agent: string
  timestamp: string
  onClick?: () => void
}

const STATUS_COLORS = {
  pending: 'var(--color-warn)',
  in_progress: 'var(--color-cyan)',
  completed: 'var(--color-ok)',
  blocked: 'var(--color-danger)',
} as const

const STATUS_LABELS = {
  pending: 'PENDING',
  in_progress: 'ACTIVE',
  completed: 'DONE',
  blocked: 'BLOCKED',
} as const

export function TaskBlock({ title, status, agent, timestamp, onClick }: TaskBlockProps) {
  const color = STATUS_COLORS[status]

  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2.5 rounded transition-colors"
      style={{
        background: 'var(--color-surface-raised)',
        borderLeft: `3px solid ${color}`,
        border: '1px solid var(--color-border)',
        borderLeftColor: color,
        borderLeftWidth: '3px',
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className="font-mono text-xs uppercase tracking-wider"
          style={{ color }}
        >
          {STATUS_LABELS[status]}
        </span>
        <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
          {agent}
        </span>
      </div>
      <p className="text-sm truncate" style={{ color: 'var(--color-text-primary)' }}>
        {title}
      </p>
      <p className="text-xs mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
        {new Date(timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
      </p>
    </button>
  )
}
