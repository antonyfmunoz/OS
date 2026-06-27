import {
  Minus,
  Plus,
  RotateCcw,
  Maximize2,
  LayoutDashboard,
  PanelLeft,
} from 'lucide-react'

interface CanvasToolbarProps {
  zoom: number
  onZoomIn: () => void
  onZoomOut: () => void
  onZoomReset: () => void
  onFitAll: () => void
  onTile: () => void
  onTogglePalette: () => void
  paletteOpen: boolean
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

export function CanvasToolbar({
  zoom,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onFitAll,
  onTile,
  onTogglePalette,
  paletteOpen,
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
    </div>
  )
}
