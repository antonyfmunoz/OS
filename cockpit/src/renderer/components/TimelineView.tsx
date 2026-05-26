interface TimelineEvent {
  id: string
  label: string
  timestamp: string
  status?: string
  dependsOn?: string[]
}

interface TimelineViewProps {
  events: TimelineEvent[]
  onEventClick?: (event: TimelineEvent) => void
}

const STATUS_COLORS: Record<string, string> = {
  completed: 'var(--color-ok)',
  in_progress: 'var(--color-cyan)',
  pending: 'var(--color-text-tertiary)',
  blocked: 'var(--color-danger)',
  active: 'var(--color-ok)',
  running: 'var(--color-cyan)',
}

export function TimelineView({ events, onEventClick }: TimelineViewProps) {
  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
          No timeline events
        </span>
      </div>
    )
  }

  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  )

  const earliest = new Date(sorted[0].timestamp).getTime()
  const latest = new Date(sorted[sorted.length - 1].timestamp).getTime()
  const range = latest - earliest || 1

  const eventMap = new Map(sorted.map((e) => [e.id, e]))

  return (
    <div className="relative w-full overflow-x-auto" style={{ minHeight: 120 }}>
      <svg width="100%" height={sorted.length * 32 + 40} className="block">
        {/* Dependency arrows */}
        {sorted.map((event, i) =>
          (event.dependsOn || []).map((depId) => {
            const depIdx = sorted.findIndex((e) => e.id === depId)
            if (depIdx < 0) return null
            const depEvent = sorted[depIdx]
            const x1 = ((new Date(depEvent.timestamp).getTime() - earliest) / range) * 85 + 10
            const y1 = depIdx * 32 + 28
            const x2 = ((new Date(event.timestamp).getTime() - earliest) / range) * 85 + 10
            const y2 = i * 32 + 28
            return (
              <line
                key={`${event.id}-${depId}`}
                x1={`${x1}%`}
                y1={y1}
                x2={`${x2}%`}
                y2={y2}
                stroke="var(--color-border)"
                strokeWidth={1}
                strokeDasharray="4 2"
                opacity={0.5}
              />
            )
          })
        )}

        {/* Event markers */}
        {sorted.map((event, i) => {
          const xPercent = ((new Date(event.timestamp).getTime() - earliest) / range) * 85 + 10
          const y = i * 32 + 28
          const color = STATUS_COLORS[event.status || ''] || 'var(--color-text-tertiary)'

          return (
            <g
              key={event.id}
              onClick={() => onEventClick?.(event)}
              style={{ cursor: onEventClick ? 'pointer' : 'default' }}
            >
              <circle
                cx={`${xPercent}%`}
                cy={y}
                r={5}
                fill={color}
                opacity={0.8}
              />
              <text
                x={`${xPercent + 2}%`}
                y={y + 4}
                fontSize={10}
                fill="var(--color-text-secondary)"
              >
                {event.label.length > 30 ? event.label.slice(0, 30) + '...' : event.label}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
