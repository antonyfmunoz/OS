interface AgentCardProps {
  name: string
  status: string
  role: string
  skills: string[]
  lastAction?: string
  lastActive?: string
  selected?: boolean
  onClick?: () => void
}

const STATUS_COLORS: Record<string, string> = {
  active: 'var(--color-ok)',
  running: 'var(--color-ok)',
  idle: 'var(--color-warn)',
  error: 'var(--color-danger)',
  stopped: 'var(--color-text-tertiary)',
}

export function AgentCard({
  name,
  status,
  role,
  skills,
  lastAction,
  lastActive,
  selected,
  onClick,
}: AgentCardProps) {
  const statusColor = STATUS_COLORS[status] || 'var(--color-text-tertiary)'

  return (
    <div
      onClick={onClick}
      className="px-3 py-2.5 rounded-md transition-colors"
      style={{
        background: selected ? 'var(--color-surface-raised)' : 'transparent',
        border: `1px solid ${selected ? 'var(--color-cyan)' : 'var(--color-border)'}`,
        cursor: onClick ? 'pointer' : 'default',
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ background: statusColor }}
        />
        <span className="text-sm font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
          {name}
        </span>
        <span
          className="text-xs px-1.5 py-0.5 rounded ml-auto flex-shrink-0"
          style={{ color: 'var(--color-text-tertiary)', background: 'var(--color-surface-raised)' }}
        >
          {status}
        </span>
      </div>

      <p className="text-xs mb-1" style={{ color: 'var(--color-text-secondary)' }}>
        {role}
      </p>

      {skills.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-1">
          {skills.slice(0, 4).map((skill) => (
            <span
              key={skill}
              className="text-xs px-1 py-0.5 rounded"
              style={{
                color: 'var(--color-cyan)',
                background: 'var(--color-cyan-glow)',
                fontSize: 10,
              }}
            >
              {skill}
            </span>
          ))}
          {skills.length > 4 && (
            <span className="text-xs" style={{ color: 'var(--color-text-tertiary)', fontSize: 10 }}>
              +{skills.length - 4}
            </span>
          )}
        </div>
      )}

      {lastAction && (
        <p className="text-xs truncate" style={{ color: 'var(--color-text-tertiary)' }}>
          {lastAction}
        </p>
      )}

      {lastActive && (
        <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-tertiary)', fontSize: 10 }}>
          {new Date(lastActive).toLocaleTimeString()}
        </p>
      )}
    </div>
  )
}
