import { useState, useRef, useCallback } from 'react'
import {
  Globe,
  Monitor,
  Camera,
  Terminal,
  Eye,
  Bot,
  LayoutGrid,
  ChevronRight,
  Plus,
  Layers,
  Workflow,
  GitBranch,
  Users,
  Maximize2,
  LayoutDashboard,
  Zap,
  RefreshCw,
  Play,
  Square,
} from 'lucide-react'
import type { CanvasMode, SavedCanvas } from '../../stores/unifiedCanvasStore'
import { ROUTES } from '../../types/routes'

interface PaletteItem {
  type?: string
  label: string
  icon: React.ReactNode
  config?: Record<string, string>
  action?: string
  submenu?: boolean
}

const GENERAL_ITEMS: PaletteItem[] = [
  { type: 'browser', label: 'Browser Pane', icon: <Globe size={14} /> },
  { label: 'Desktop', icon: <Monitor size={14} />, submenu: true },
  { label: 'Vision', icon: <Camera size={14} />, submenu: true },
  { label: 'Terminal', icon: <Terminal size={14} />, submenu: true },
  { type: 'preview', label: 'Live Preview', icon: <Eye size={14} /> },
  { label: 'Agent', icon: <Bot size={14} />, submenu: true },
  { label: 'Panel', icon: <LayoutGrid size={14} />, submenu: true },
]

const DESKTOP_MONITORS = [
  { id: 'M0', label: 'BenQ XL2720Z' },
  { id: 'M1', label: 'DELL AW2518HF' },
]

const VISION_CAMERAS = [
  { id: 'default', label: 'Insta360 Link 2' },
]

const AGENT_ITEMS: PaletteItem[] = [
  { label: 'Show All Agents', icon: <Users size={14} />, action: 'showAll' },
  { label: 'Tile All', icon: <LayoutDashboard size={14} />, action: 'tile' },
  { label: 'Fit All', icon: <Maximize2 size={14} />, action: 'fitAll' },
  { label: 'Agents', icon: <Bot size={14} />, submenu: true },
]

const WORKFLOW_ITEMS: PaletteItem[] = [
  { label: 'Add Action Node', icon: <Zap size={14} />, action: 'addAction' },
  { label: 'Add Condition Node', icon: <GitBranch size={14} />, action: 'addCondition' },
  { label: 'Add Trigger Node', icon: <Workflow size={14} />, action: 'addTrigger' },
]

const LOOP_ITEMS: PaletteItem[] = [
  { label: 'Refresh Loops', icon: <RefreshCw size={14} />, action: 'refreshLoops' },
  { label: 'Create Loop', icon: <Plus size={14} />, action: 'createLoop' },
  { label: 'Start All', icon: <Play size={14} />, action: 'startAll' },
  { label: 'Stop All', icon: <Square size={14} />, action: 'stopAll' },
]

const HARNESS_ITEMS: PaletteItem[] = [
  { label: 'Refresh Runtimes', icon: <RefreshCw size={14} />, action: 'refreshRuntimes' },
  { label: 'Show Available', icon: <Zap size={14} />, action: 'showAvailable' },
  { label: 'Show All', icon: <Layers size={14} />, action: 'showAll' },
]

const ORGANISM_ITEMS: PaletteItem[] = [
  { label: 'Refresh Topology', icon: <RefreshCw size={14} />, action: 'refreshTopology' },
  { label: 'Show All Nodes', icon: <Users size={14} />, action: 'showAllNodes' },
  { label: 'Fit View', icon: <Maximize2 size={14} />, action: 'fitView' },
]

const MODE_ITEMS: Record<CanvasMode, PaletteItem[]> = {
  general: GENERAL_ITEMS,
  agents: AGENT_ITEMS,
  workflows: WORKFLOW_ITEMS,
  loops: LOOP_ITEMS,
  harnesses: HARNESS_ITEMS,
  organism: ORGANISM_ITEMS,
}

const PANEL_ROUTES = ROUTES.filter(
  (r) => r.visibility === 'primary' && r.id !== 'canvas' && r.id !== 'agents' && r.id !== 'workflows',
)

interface CanvasPaletteProps {
  mode: CanvasMode
  onAddWindow: (type: string, config?: Record<string, string>) => void
  onAction: (action: string) => void
  savedCanvases: SavedCanvas[]
  activeCanvasId: string | null
  onCreateCanvas: (name: string) => void
  onLoadCanvas: (id: string) => void
  onRenameCanvas: (id: string, name: string) => void
  onDeleteCanvas: (id: string) => void
  open?: boolean
  onToggle?: () => void
  agents?: Array<{ id: string; name: string }>
  tmuxSessions?: Array<{ name: string; windows: number }>
}

export function CanvasPalette({
  mode,
  onAddWindow,
  onAction,
  savedCanvases,
  activeCanvasId,
  onCreateCanvas,
  onLoadCanvas,
  onRenameCanvas,
  onDeleteCanvas,
  open,
  onToggle,
  agents,
  tmuxSessions,
}: CanvasPaletteProps) {
  const [internalExpanded, setInternalExpanded] = useState(false)
  const expanded = open ?? internalExpanded
  const toggle = onToggle ?? (() => setInternalExpanded((v) => !v))

  const [panelSubmenuOpen, setPanelSubmenuOpen] = useState(false)
  const [agentSubmenuOpen, setAgentSubmenuOpen] = useState(false)
  const [terminalSubmenuOpen, setTerminalSubmenuOpen] = useState(false)
  const [generalAgentSubmenuOpen, setGeneralAgentSubmenuOpen] = useState(false)
  const [desktopSubmenuOpen, setDesktopSubmenuOpen] = useState(false)
  const [visionSubmenuOpen, setVisionSubmenuOpen] = useState(false)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [creatingCanvas, setCreatingCanvas] = useState(false)
  const [newCanvasName, setNewCanvasName] = useState('')
  const renameRef = useRef<HTMLInputElement>(null)
  const createRef = useRef<HTMLInputElement>(null)

  const items = MODE_ITEMS[mode]

  const commitRename = useCallback(() => {
    if (renamingId && renameValue.trim()) {
      onRenameCanvas(renamingId, renameValue.trim())
    }
    setRenamingId(null)
    setRenameValue('')
  }, [renamingId, renameValue, onRenameCanvas])

  const startRename = useCallback((canvas: SavedCanvas) => {
    setRenamingId(canvas.id)
    setRenameValue(canvas.name)
    setTimeout(() => renameRef.current?.select(), 0)
  }, [])

  const handleCreateCanvas = useCallback(() => {
    if (newCanvasName.trim()) {
      onCreateCanvas(newCanvasName.trim())
      setNewCanvasName('')
      setCreatingCanvas(false)
    }
  }, [newCanvasName, onCreateCanvas])

  const handleDeleteCanvas = useCallback(
    (canvas: SavedCanvas) => {
      if (confirm(`Delete canvas "${canvas.name}"?`)) {
        onDeleteCanvas(canvas.id)
      }
    },
    [onDeleteCanvas],
  )

  const modeCanvases = savedCanvases.filter((c) => c.mode === mode)

  return (
    <div
      className="h-full flex"
      style={{
        width: expanded ? 200 : 0,
        transition: 'width 200ms ease',
        overflow: 'hidden',
      }}
    >
      <div
        className="h-full flex flex-col shrink-0 overflow-y-auto overflow-x-hidden"
        style={{
          width: 200,
          background: 'var(--color-surface)',
          borderRight: '1px solid var(--color-border)',
        }}
      >
        {/* Section 1: Add to Canvas */}
        <div
          className="px-3 pt-2 pb-1 text-[10px] uppercase tracking-wider"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          Add to Canvas
        </div>
        <div className="flex flex-col gap-0.5 px-1">
          {items.map((item, i) => (
            <div key={`${item.label}-${i}`}>
              <PaletteButton
                label={item.label}
                icon={item.icon}
                suffix={item.submenu ? <ChevronRight size={10} style={{ color: 'var(--color-text-tertiary)' }} /> : undefined}
                onClick={() => {
                  if (item.submenu && item.label === 'Panel') {
                    setPanelSubmenuOpen((v) => !v)
                  } else if (item.submenu && item.label === 'Agents') {
                    setAgentSubmenuOpen((v) => !v)
                  } else if (item.submenu && item.label === 'Terminal') {
                    setTerminalSubmenuOpen((v) => !v)
                  } else if (item.submenu && item.label === 'Agent') {
                    setGeneralAgentSubmenuOpen((v) => !v)
                  } else if (item.submenu && item.label === 'Desktop') {
                    setDesktopSubmenuOpen((v) => !v)
                  } else if (item.submenu && item.label === 'Vision') {
                    setVisionSubmenuOpen((v) => !v)
                  } else if (item.type) {
                    onAddWindow(item.type, item.config)
                  } else if (item.action) {
                    onAction(item.action)
                  }
                }}
              />

              {/* Desktop submenu — inline after Desktop button */}
              {item.label === 'Desktop' && item.submenu && desktopSubmenuOpen && mode === 'general' && (
                <div className="flex flex-col gap-0.5 px-1 ml-3 mt-0.5" style={{ borderLeft: '2px solid var(--color-border)' }}>
                  {DESKTOP_MONITORS.map((m) => (
                    <PaletteButton
                      key={m.id}
                      label={m.label}
                      icon={<Monitor size={12} />}
                      onClick={() => {
                        onAddWindow('desktop', { monitorId: m.id })
                        setDesktopSubmenuOpen(false)
                      }}
                    />
                  ))}
                </div>
              )}

              {/* Vision submenu — inline after Vision button */}
              {item.label === 'Vision' && item.submenu && visionSubmenuOpen && mode === 'general' && (
                <div className="flex flex-col gap-0.5 px-1 ml-3 mt-0.5" style={{ borderLeft: '2px solid var(--color-border)' }}>
                  {VISION_CAMERAS.map((c) => (
                    <PaletteButton
                      key={c.id}
                      label={c.label}
                      icon={<Camera size={12} />}
                      onClick={() => {
                        onAddWindow('vision', { cameraId: c.id })
                        setVisionSubmenuOpen(false)
                      }}
                    />
                  ))}
                </div>
              )}

              {/* Terminal submenu — inline after Terminal button */}
              {item.label === 'Terminal' && item.submenu && terminalSubmenuOpen && mode === 'general' && (
                <div className="flex flex-col gap-0.5 px-1 ml-3 mt-0.5" style={{ borderLeft: '2px solid var(--color-border)', maxHeight: 200, overflowY: 'auto' }}>
                  {(tmuxSessions && tmuxSessions.length > 0 ? tmuxSessions : [{ name: 'dex_main', windows: 1 }, { name: 'ai_main', windows: 1 }]).map((s) => (
                    <PaletteButton
                      key={s.name}
                      label={s.name}
                      icon={<Terminal size={12} />}
                      onClick={() => {
                        onAddWindow('terminal', { session: s.name, pane: '0' })
                        setTerminalSubmenuOpen(false)
                      }}
                    />
                  ))}
                </div>
              )}

              {/* Agent submenu — inline after Agent button (general mode) */}
              {item.label === 'Agent' && item.submenu && generalAgentSubmenuOpen && mode === 'general' && (
                <div className="flex flex-col gap-0.5 px-1 ml-3 mt-0.5" style={{ borderLeft: '2px solid var(--color-border)', maxHeight: 200, overflowY: 'auto' }}>
                  {agents && agents.length > 0 ? agents.map((a) => (
                    <PaletteButton
                      key={a.id}
                      label={a.name}
                      icon={<Bot size={12} />}
                      onClick={() => {
                        onAddWindow('agent', { agentId: a.id, agentName: a.name })
                        setGeneralAgentSubmenuOpen(false)
                      }}
                    />
                  )) : (
                    <div className="px-2 py-1.5 text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>
                      No agents registered
                    </div>
                  )}
                </div>
              )}

              {/* Panel submenu — inline after Panel button */}
              {item.label === 'Panel' && item.submenu && panelSubmenuOpen && mode === 'general' && (
                <div className="flex flex-col gap-0.5 px-1 ml-3 mt-0.5" style={{ borderLeft: '2px solid var(--color-border)' }}>
                  {PANEL_ROUTES.map((route) => {
                    const Icon = route.icon
                    return (
                      <PaletteButton
                        key={route.id}
                        label={route.label}
                        icon={<Icon size={12} />}
                        onClick={() => {
                          onAddWindow('panel', { panelId: route.id })
                          setPanelSubmenuOpen(false)
                        }}
                      />
                    )
                  })}
                </div>
              )}

              {/* Agents submenu — inline after Agents button (agents mode) */}
              {item.label === 'Agents' && item.submenu && agentSubmenuOpen && mode === 'agents' && (
                <div className="flex flex-col gap-0.5 px-1 ml-3 mt-0.5" style={{ borderLeft: '2px solid var(--color-border)', maxHeight: 200, overflowY: 'auto' }}>
                  {agents && agents.length > 0 ? agents.map((a) => (
                    <PaletteButton
                      key={a.id}
                      label={a.name}
                      icon={<Bot size={12} />}
                      onClick={() => {
                        onAddWindow('agent', { agentId: a.id, agentName: a.name })
                      }}
                    />
                  )) : (
                    <div className="px-2 py-1.5 text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>
                      No agents registered
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Divider */}
        <div className="mx-2 my-2" style={{ borderTop: '1px solid var(--color-border)' }} />

        {/* Section 2: Saved Canvases */}
        <div
          className="px-3 pb-1 text-[10px] uppercase tracking-wider flex items-center gap-1"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          <Layers size={10} />
          Saved Canvases
        </div>
        <div className="flex flex-col gap-0.5 px-1 pb-2">
          {modeCanvases.length === 0 && !creatingCanvas && (
            <div className="px-2 py-1.5 text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>
              No saved canvases
            </div>
          )}
          {modeCanvases.map((canvas) => (
            <div key={canvas.id}>
              {renamingId === canvas.id ? (
                <input
                  ref={renameRef}
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onBlur={commitRename}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') commitRename()
                    if (e.key === 'Escape') {
                      setRenamingId(null)
                      setRenameValue('')
                    }
                  }}
                  className="w-full text-[12px] px-2 py-1 rounded outline-none mx-1"
                  style={{
                    background: 'var(--color-surface)',
                    color: 'var(--color-text-primary)',
                    border: '1px solid var(--color-border-active)',
                  }}
                />
              ) : (
                <button
                  className="flex items-center gap-2 w-full px-2 py-1.5 rounded text-[12px] text-left"
                  style={{
                    color: canvas.id === activeCanvasId ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                    borderLeft: canvas.id === activeCanvasId ? '2px solid var(--color-cyan)' : '2px solid transparent',
                    fontWeight: canvas.id === activeCanvasId ? 500 : 400,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--color-surface-overlay)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent'
                  }}
                  onClick={() => onLoadCanvas(canvas.id)}
                  onDoubleClick={(e) => {
                    e.stopPropagation()
                    startRename(canvas)
                  }}
                  onContextMenu={(e) => {
                    e.preventDefault()
                    handleDeleteCanvas(canvas)
                  }}
                >
                  <span className="truncate">{canvas.name}</span>
                </button>
              )}
            </div>
          ))}

          {/* New canvas input */}
          {creatingCanvas ? (
            <input
              ref={createRef}
              value={newCanvasName}
              onChange={(e) => setNewCanvasName(e.target.value)}
              onBlur={() => {
                if (newCanvasName.trim()) handleCreateCanvas()
                else setCreatingCanvas(false)
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreateCanvas()
                if (e.key === 'Escape') {
                  setCreatingCanvas(false)
                  setNewCanvasName('')
                }
              }}
              placeholder="Canvas name..."
              className="w-full text-[12px] px-2 py-1 rounded outline-none mx-1"
              style={{
                background: 'var(--color-surface)',
                color: 'var(--color-text-primary)',
                border: '1px solid var(--color-border-active)',
              }}
              autoFocus
            />
          ) : (
            <PaletteButton
              label="New Canvas"
              icon={<Plus size={14} />}
              onClick={() => {
                setCreatingCanvas(true)
                setNewCanvasName('')
                setTimeout(() => createRef.current?.focus(), 0)
              }}
            />
          )}
        </div>
      </div>
    </div>
  )
}

function PaletteButton({
  label,
  icon,
  suffix,
  onClick,
}: {
  label: string
  icon: React.ReactNode
  suffix?: React.ReactNode
  onClick: () => void
}) {
  return (
    <button
      className="flex items-center gap-2 w-full px-2 py-1.5 rounded text-[12px] text-left"
      style={{ color: 'var(--color-text-secondary)' }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--color-surface-overlay)'
        e.currentTarget.style.color = 'var(--color-text-primary)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'transparent'
        e.currentTarget.style.color = 'var(--color-text-secondary)'
      }}
      onClick={onClick}
    >
      {icon}
      <span className="flex-1 truncate">{label}</span>
      {suffix}
    </button>
  )
}
