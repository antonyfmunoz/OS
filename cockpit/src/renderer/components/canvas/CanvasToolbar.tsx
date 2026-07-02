import { useState, useRef, useEffect } from 'react'
import {
  Minus,
  Plus,
  RotateCcw,
  PanelLeft,
  ChevronDown,
  Layers,
  Bot,
  Workflow,
  RefreshCcw,
  Cpu,
  Brain,
  PanelRight,
  FileStack,
  Plus as PlusIcon,
} from 'lucide-react'
import { useUnifiedCanvasStore, type CanvasMode } from '../../stores/unifiedCanvasStore'
import { useCockpitStore } from '../../stores/cockpitStore'

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

function CanvasDropdown() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const activeMode = useUnifiedCanvasStore((s) => s.activeMode)
  const savedCanvases = useUnifiedCanvasStore((s) => s.savedCanvases)
  const activeCanvasId = useUnifiedCanvasStore((s) => s.activeCanvasId)
  const setActiveCanvas = useUnifiedCanvasStore((s) => s.setActiveCanvas)
  const createCanvas = useUnifiedCanvasStore((s) => s.createCanvas)

  const modeCanvases = savedCanvases.filter((c) => c.mode === activeMode)
  const currentId = activeCanvasId[activeMode]
  const currentName = modeCanvases.find((c) => c.id === currentId)?.name ?? 'Default'

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
        title="Select canvas"
      >
        <FileStack size={12} />
        <span className="max-w-[80px] truncate">{currentName}</span>
        <ChevronDown size={10} />
      </button>
      {open && (
        <div
          className="absolute bottom-full left-0 mb-1 py-1 rounded"
          style={{
            background: 'var(--color-surface-raised)',
            border: '1px solid var(--color-border)',
            boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
            minWidth: 160,
          }}
        >
          <button
            className="flex items-center gap-2 w-full px-3 py-1.5 text-[11px] text-left"
            style={{
              color: !currentId ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
              background: !currentId ? 'var(--color-surface-overlay)' : 'transparent',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-surface-overlay)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = !currentId ? 'var(--color-surface-overlay)' : 'transparent' }}
            onClick={() => { setActiveCanvas(activeMode, null); setOpen(false) }}
          >
            Default
          </button>
          {modeCanvases.map((c) => (
            <button
              key={c.id}
              className="flex items-center gap-2 w-full px-3 py-1.5 text-[11px] text-left"
              style={{
                color: c.id === currentId ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                background: c.id === currentId ? 'var(--color-surface-overlay)' : 'transparent',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-surface-overlay)' }}
              onMouseLeave={(e) => { e.currentTarget.style.background = c.id === currentId ? 'var(--color-surface-overlay)' : 'transparent' }}
              onClick={() => { setActiveCanvas(activeMode, c.id); setOpen(false) }}
            >
              <span className="truncate">{c.name}</span>
            </button>
          ))}
          <div className="my-1 border-t border-border" />
          <button
            className="flex items-center gap-2 w-full px-3 py-1.5 text-[11px] text-left text-cyan"
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-surface-overlay)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
            onClick={() => {
              const name = prompt('Canvas name:')
              if (name?.trim()) {
                createCanvas(name.trim())
                setOpen(false)
              }
            }}
          >
            <PlusIcon size={10} />
            New Canvas
          </button>
        </div>
      )}
    </div>
  )
}

function ChatToggle() {
  const rightDrawerOpen = useCockpitStore((s) => s.rightDrawerOpen)
  const toggleRightDrawer = useCockpitStore((s) => s.toggleRightDrawer)
  return (
    <ToolbarButton
      onClick={toggleRightDrawer}
      title={rightDrawerOpen ? 'Hide chat' : 'Open chat'}
      active={rightDrawerOpen}
    >
      <PanelRight size={14} />
    </ToolbarButton>
  )
}

export function CanvasToolbar({
  zoom,
  onZoomIn,
  onZoomOut,
  onZoomReset,
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
        borderRadius: 4,
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

      {extraButtons && (
        <>
          <Separator />
          {extraButtons}
        </>
      )}

      <Separator />

      <CanvasDropdown />

      <Separator />

      <ChatToggle />
    </div>
  )
}
