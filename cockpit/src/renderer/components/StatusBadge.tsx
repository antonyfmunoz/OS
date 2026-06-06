const STATUS_STYLES: Record<string, { color: string; bg: string }> = {
  active: { color: 'var(--color-ok)', bg: 'rgba(0,255,136,0.12)' },
  running: { color: 'var(--color-ok)', bg: 'rgba(0,255,136,0.12)' },
  executing: { color: 'var(--color-ok)', bg: 'rgba(0,255,136,0.12)' },
  completed: { color: 'var(--color-ok)', bg: 'rgba(0,255,136,0.12)' },
  idle: { color: 'var(--color-warn)', bg: 'rgba(255,184,0,0.12)' },
  paused: { color: 'var(--color-warn)', bg: 'rgba(255,184,0,0.12)' },
  blocked: { color: 'var(--color-warn)', bg: 'rgba(255,184,0,0.12)' },
  pending: { color: 'var(--color-text-secondary)', bg: 'var(--color-surface-raised)' },
  drafted: { color: 'var(--color-text-tertiary)', bg: 'var(--color-surface-raised)' },
  error: { color: 'var(--color-danger)', bg: 'rgba(255,61,61,0.12)' },
  failed: { color: 'var(--color-danger)', bg: 'rgba(255,61,61,0.12)' },
  stopped: { color: 'var(--color-text-tertiary)', bg: 'var(--color-surface-raised)' },
}

interface StatusBadgeProps {
  status: string
  dot?: boolean
}

export function StatusBadge({ status, dot }: StatusBadgeProps) {
  const style = STATUS_STYLES[status.toLowerCase()] || STATUS_STYLES.pending

  return (
    <span
      className="inline-flex items-center gap-1 text-[9px] font-mono uppercase px-1.5 py-0.5 rounded"
      style={{ color: style.color, background: style.bg, letterSpacing: '0.05em' }}
    >
      {dot && (
        <span
          data-testid="status-dot"
          className="w-1.5 h-1.5 rounded-full flex-shrink-0"
          style={{ background: style.color }}
        />
      )}
      {status.toUpperCase()}
    </span>
  )
}
