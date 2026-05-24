interface OverlayOption {
  id: string
  label: string
  color?: string
}

interface OverlayToggleProps {
  options: OverlayOption[]
  active: string[]
  onToggle: (id: string) => void
}

export function OverlayToggle({ options, active, onToggle }: OverlayToggleProps) {
  return (
    <div className="flex flex-wrap gap-1">
      {options.map((opt) => {
        const isActive = active.includes(opt.id)
        return (
          <button
            key={opt.id}
            onClick={() => onToggle(opt.id)}
            className="px-2 py-1 rounded text-xs transition-colors"
            style={{
              color: isActive ? (opt.color || 'var(--accent-cyan)') : 'var(--text-tertiary)',
              background: isActive ? 'var(--glow-cyan)' : 'var(--surface-2)',
              border: `1px solid ${isActive ? (opt.color || 'var(--accent-cyan)') : 'var(--border)'}`,
            }}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
