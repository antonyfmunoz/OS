interface TaskBlockProps {
  id: string
  title: string
  status: 'pending' | 'in_progress' | 'completed' | 'blocked'
  agent: string
  timestamp: string
  onClick?: () => void
}

const STATUS_COLORS = {
  pending: 'var(--accent-amber)',
  in_progress: 'var(--accent-cyan)',
  completed: 'var(--accent-green)',
  blocked: 'var(--accent-red)',
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
        background: 'var(--surface-2)',
        borderLeft: `3px solid ${color}`,
        border: '1px solid var(--border)',
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
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
          {agent}
        </span>
      </div>
      <p className="text-sm truncate" style={{ color: 'var(--text-primary)' }}>
        {title}
      </p>
      <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
        {new Date(timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
      </p>
    </button>
  )
}
