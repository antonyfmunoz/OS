import { useState, useRef, useEffect } from 'react'
import { Monitor, Tablet, Smartphone, ChevronDown } from 'lucide-react'

export type ViewportPreset = 'desktop' | 'tablet' | 'mobile'

interface ViewportConfig {
  label: string
  width: number
  height: number
  icon: typeof Monitor
}

export const VIEWPORT_PRESETS: Record<ViewportPreset, ViewportConfig> = {
  desktop: { label: 'Desktop', width: 1440, height: 900, icon: Monitor },
  tablet: { label: 'Tablet', width: 768, height: 1024, icon: Tablet },
  mobile: { label: 'Mobile', width: 375, height: 812, icon: Smartphone },
}

interface ViewportSelectorProps {
  value: ViewportPreset
  onChange: (preset: ViewportPreset) => void
}

export function ViewportSelector({ value, onChange }: ViewportSelectorProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const active = VIEWPORT_PRESETS[value]
  const ActiveIcon = active.icon

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
        style={{
          color: 'var(--color-text-secondary)',
          border: '1px solid var(--color-border)',
        }}
      >
        <ActiveIcon size={12} />
        <span>{active.label}</span>
        <ChevronDown size={10} />
      </button>
      {open && (
        <div
          className="absolute top-full right-0 mt-1 rounded shadow-lg z-50 min-w-[160px]"
          style={{
            background: 'var(--color-surface-raised)',
            border: '1px solid var(--color-border)',
          }}
        >
          {(Object.entries(VIEWPORT_PRESETS) as [ViewportPreset, ViewportConfig][]).map(
            ([key, cfg]) => {
              const Icon = cfg.icon
              const selected = key === value
              return (
                <button
                  key={key}
                  onClick={() => { onChange(key); setOpen(false) }}
                  className="flex items-center gap-2 w-full text-left px-3 py-1.5 text-xs hover:opacity-80"
                  style={{
                    color: selected ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                  }}
                >
                  <Icon size={12} />
                  <span className="flex-1">{cfg.label}</span>
                  <span
                    className="text-[10px]"
                    style={{ color: 'var(--color-text-tertiary)' }}
                  >
                    {cfg.width}×{cfg.height}
                  </span>
                </button>
              )
            },
          )}
        </div>
      )}
    </div>
  )
}
