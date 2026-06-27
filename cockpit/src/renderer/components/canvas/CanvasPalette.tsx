import { useState } from 'react'
import {
  Globe,
  Monitor,
  Camera,
  Terminal,
  Eye,
  Bot,
  LayoutGrid,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react'

interface PaletteItem {
  type: string
  label: string
  icon: React.ReactNode
  config?: Record<string, string>
}

const ITEMS: PaletteItem[] = [
  { type: 'browser', label: 'Browser Pane', icon: <Globe size={14} /> },
  { type: 'desktop', label: 'Desktop M0', icon: <Monitor size={14} />, config: { monitorId: 'M0' } },
  { type: 'desktop', label: 'Desktop M1', icon: <Monitor size={14} />, config: { monitorId: 'M1' } },
  { type: 'vision', label: 'Vision Camera', icon: <Camera size={14} /> },
  { type: 'terminal', label: 'Terminal', icon: <Terminal size={14} /> },
  { type: 'preview', label: 'Live Preview', icon: <Eye size={14} /> },
  { type: 'agent', label: 'Agent', icon: <Bot size={14} /> },
  { type: 'panel', label: 'Panel', icon: <LayoutGrid size={14} /> },
]

interface CanvasPaletteProps {
  onAddWindow: (type: string, config?: Record<string, string>) => void
  open?: boolean
  onToggle?: () => void
}

export function CanvasPalette({ onAddWindow, open, onToggle }: CanvasPaletteProps) {
  const [internalExpanded, setInternalExpanded] = useState(false)
  const expanded = open ?? internalExpanded
  const toggle = onToggle ?? (() => setInternalExpanded((v) => !v))

  return (
    <div
      className="h-full flex"
      style={{
        width: expanded ? 160 : 0,
        transition: 'width 200ms ease',
        overflow: 'hidden',
      }}
    >
      {/* Panel body */}
      <div
        className="h-full flex flex-col py-2 gap-1 shrink-0"
        style={{
          width: 160,
          background: 'var(--color-surface)',
          borderRight: '1px solid var(--color-border)',
        }}
      >
        <div
          className="px-3 pb-1 text-[10px] uppercase tracking-wider"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          Add Window
        </div>
        {ITEMS.map((item, i) => (
          <button
            key={`${item.type}-${i}`}
            className="flex items-center gap-2 px-3 py-1.5 mx-1 rounded text-[12px] text-left"
            style={{ color: 'var(--color-text-secondary)' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--color-surface-overlay)'
              e.currentTarget.style.color = 'var(--color-text-primary)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = 'var(--color-text-secondary)'
            }}
            onClick={() => onAddWindow(item.type, item.config)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </div>

      {/* Toggle tab — sits at the right edge of the palette area */}
      <button
        className="absolute top-1/2 -translate-y-1/2 flex items-center justify-center rounded-r"
        style={{
          left: expanded ? 160 : 0,
          width: 16,
          height: 48,
          background: 'var(--color-surface-raised)',
          border: '1px solid var(--color-border)',
          borderLeft: 'none',
          color: 'var(--color-text-tertiary)',
          transition: 'left 200ms ease',
          zIndex: 11,
        }}
        onClick={toggle}
        title={expanded ? 'Collapse palette' : 'Expand palette'}
      >
        {expanded ? <ChevronLeft size={12} /> : <ChevronRight size={12} />}
      </button>
    </div>
  )
}
