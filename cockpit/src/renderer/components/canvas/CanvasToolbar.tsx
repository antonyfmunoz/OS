import { useState, useRef, useEffect } from 'react'
import {
  Minus,
  Plus,
  RotateCcw,
  Maximize2,
  LayoutDashboard,
  PanelLeft,
  ChevronDown,
  Layers,
  Bot,
  Workflow,
  RefreshCcw,
  Cpu,
  Brain,
} from 'lucide-react'
import type { CanvasMode } from '../../stores/unifiedCanvasStore'

const MODE_ORDER: CanvasMode[] = ['general', 'organism', 'agents', 'harnesses', 'loops', 'workflows']

const MODE_META: Record<CanvasMode, { label: string; icon: typeof Layers }> = {
  general: { label: 'General', icon: Layers },
  organism: { label: 'Organism', icon: Brain },
  agents: { label: 'Agents', icon: Bot },
  harnesses: { label: 'Harnesses', icon: Cpu },
  loops: { label: 'Loops', icon: RefreshCcw },
  workflows: { label: 'Workflows', icon: Workflow },
}

interface CanvasToolbarProps {
  zoom: number
  onZoomIn: () => void
  onZoomOut: () => void
  onZoomReset: () => void
  onFitAll: () => void
  onTile: () => void
  onTogglePalette: () => void
  paletteOpen: boolean
  mode?: CanvasMode
  onSetMode?: (mode: CanvasMode) => void
  extraButtons?: React.ReactNode
}

function ToolbarButton({
  onClick,
  title,
  active,
  children,
}: {
  onClick: () => void
  title: string
  active?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="flex items-center justify-center rounded px-1.5 py-1"
      style={{
        color: active ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
        fontSize: 11,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.color = 'var(--color-text-primary)'
        e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.color = active
          ? 'var(--color-text-primary)'
          : 'var(--color-text-secondary)'
        e.currentTarget.style.background = 'transparent'
      }}
    >
      {children}
    </button>
  )
}

function Separator() {
  return (
    <div
      className="mx-1"
      style={{ width: 1, height: 16, background: 'var(--color-border)' }}
    />
  )
}

function ModeDropdown({ mode, onSetMode }: { mode: CanvasMode; onSetMode: (m: CanvasMode) => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const meta = MODE_META[mode]
  const Icon = meta.icon

  useEffect(() => {
    if (!open) return
    const close = (e: Event) => {
      const target = e.target as Node
      if (ref.current && !ref.current.contains(target)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('touchstart', close)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('touchstart', close)
    }
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 px-2 py-1 rounded"
        style={{ color: 'var(--color-text-primary)', fontSize: 11 }}
        onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
      >
        <Icon size={12} />
        <span>{meta.label}</span>
        <ChevronDown size={10} />
      </button>
      {open && (
        <div
          className="absolute bottom-full left-0 mb-1 py-1 rounded-lg"
          style={{
            background: 'var(--color-surface-raised)',
            border: '1px solid var(--color-border)',
            boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
            minWidth: 140,
          }}
        >
          {MODE_ORDER.map((m) => {
            const mi = MODE_META[m]
            const MIcon = mi.icon
            return (
              <button
                key={m}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-[12px] text-left"
                style={{
                  color: m === mode ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                  background: m === mode ? 'var(--color-surface-overlay)' : 'transparent',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-surface-overlay)' }}
                onMouseLeave={(e) => { e.currentTarget.style.background = m === mode ? 'var(--color-surface-overlay)' : 'transparent' }}
                onClick={() => { onSetMode(m); setOpen(false) }}
              >
                <MIcon size={12} />
                <span>{mi.label}</span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function CanvasToolbar({
  zoom,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onFitAll,
  onTile,
  onTogglePalette,
  paletteOpen,
  mode,
  onSetMode,
  extraButtons,
}: CanvasToolbarProps) {
  return (
    <div
      className="flex items-center gap-0.5 px-3"
      style={{
        height: 36,
        background: 'rgba(17, 17, 17, 0.85)',
        backdropFilter: 'blur(8px)',
        border: '1px solid var(--color-border)',
        borderRadius: 9999,
      }}
    >
      <ToolbarButton
        onClick={onTogglePalette}
        title={paletteOpen ? 'Hide palette' : 'Show palette'}
        active={paletteOpen}
      >
        <PanelLeft size={14} />
      </ToolbarButton>

      <Separator />

      {mode && onSetMode && (
        <>
          <ModeDropdown mode={mode} onSetMode={onSetMode} />
          <Separator />
        </>
      )}

      <ToolbarButton onClick={onZoomOut} title="Zoom out">
        <Minus size={14} />
      </ToolbarButton>

      <span
        className="text-[11px] w-10 text-center tabular-nums select-none"
        style={{ color: 'var(--color-text-secondary)' }}
      >
        {Math.round(zoom * 100)}%
      </span>

      <ToolbarButton onClick={onZoomIn} title="Zoom in">
        <Plus size={14} />
      </ToolbarButton>

      <ToolbarButton onClick={onZoomReset} title="Reset zoom to 100%">
        <RotateCcw size={12} />
      </ToolbarButton>

      <Separator />

      <ToolbarButton onClick={onFitAll} title="Fit all windows">
        <Maximize2 size={14} />
      </ToolbarButton>

      <ToolbarButton onClick={onTile} title="Tile windows">
        <LayoutDashboard size={14} />
      </ToolbarButton>

      {extraButtons && (
        <>
          <Separator />
          {extraButtons}
        </>
      )}
    </div>
  )
}
