import { useState } from 'react'
import { Monitor, Tablet, Smartphone } from 'lucide-react'

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
  return (
    <div className="flex items-center gap-1">
      {(Object.entries(VIEWPORT_PRESETS) as [ViewportPreset, ViewportConfig][]).map(
        ([key, cfg]) => {
          const Icon = cfg.icon
          const active = key === value
          return (
            <button
              key={key}
              onClick={() => onChange(key)}
              className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
              style={{
                background: active ? 'var(--color-accent-dim)' : 'transparent',
                color: active ? 'var(--color-accent)' : 'var(--color-text-tertiary)',
                border: active ? '1px solid var(--color-accent)' : '1px solid transparent',
              }}
              title={`${cfg.label} (${cfg.width}×${cfg.height})`}
            >
              <Icon size={14} />
              <span>{cfg.label}</span>
            </button>
          )
        },
      )}
    </div>
  )
}
