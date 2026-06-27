import { useState, useCallback, useRef } from 'react'
import { useCanvasDrag } from '../../hooks/useCanvasDrag'
import { useCanvasResize, type Edge } from '../../hooks/useCanvasResize'
import { useCanvasStore, type CanvasWindow as CanvasWindowType } from '../../stores/canvasStore'
import { WindowContent } from './WindowContent'
import {
  Minus,
  Maximize2,
  Minimize2,
  X,
  ExternalLink,
  Pause,
  Play,
  ChevronDown,
  ChevronUp,
  Globe,
  Monitor,
  Camera,
  Terminal,
  Eye,
  Bot,
  LayoutGrid,
} from 'lucide-react'

const STATUS_COLORS: Record<CanvasWindowType['connectionStatus'], string> = {
  connected: '#22c55e',
  connecting: '#f59e0b',
  disconnected: '#6b7280',
  error: '#ef4444',
}

const TYPE_ICONS: Record<CanvasWindowType['type'], typeof Globe> = {
  browser: Globe,
  desktop: Monitor,
  vision: Camera,
  terminal: Terminal,
  preview: Eye,
  agent: Bot,
  panel: LayoutGrid,
}

const RESIZE_EDGES: { edge: Edge; style: React.CSSProperties }[] = [
  { edge: 'n', style: { top: -2, left: 4, right: 4, height: 4, cursor: 'ns-resize' } },
  { edge: 's', style: { bottom: -2, left: 4, right: 4, height: 4, cursor: 'ns-resize' } },
  { edge: 'e', style: { top: 4, right: -2, bottom: 4, width: 4, cursor: 'ew-resize' } },
  { edge: 'w', style: { top: 4, left: -2, bottom: 4, width: 4, cursor: 'ew-resize' } },
  { edge: 'ne', style: { top: -2, right: -2, width: 8, height: 8, cursor: 'nesw-resize' } },
  { edge: 'nw', style: { top: -2, left: -2, width: 8, height: 8, cursor: 'nwse-resize' } },
  { edge: 'se', style: { bottom: -2, right: -2, width: 8, height: 8, cursor: 'nwse-resize' } },
  { edge: 'sw', style: { bottom: -2, left: -2, width: 8, height: 8, cursor: 'nesw-resize' } },
]

interface CanvasWindowProps {
  windowId: string
  zoom: number
}

export function CanvasWindow({ windowId, zoom }: CanvasWindowProps) {
  const w = useCanvasStore((s) => s.windows.find((win) => win.id === windowId))
  const bringToFront = useCanvasStore((s) => s.bringToFront)
  const updateWindow = useCanvasStore((s) => s.updateWindow)
  const toggleCollapse = useCanvasStore((s) => s.toggleCollapse)
  const toggleMaximize = useCanvasStore((s) => s.toggleMaximize)
  const togglePause = useCanvasStore((s) => s.togglePause)
  const removeWindow = useCanvasStore((s) => s.removeWindow)
  const popOut = useCanvasStore((s) => s.popOut)
  const renameWindow = useCanvasStore((s) => s.renameWindow)

  const [renaming, setRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const renameRef = useRef<HTMLInputElement>(null)

  const drag = useCanvasDrag({
    onDragStart: () => bringToFront(windowId),
    onDrag: (x, y) => updateWindow(windowId, { x, y }),
    zoom,
  })

  const resize = useCanvasResize({
    onResize: (x, y, width, height) => updateWindow(windowId, { x, y, width, height }),
    zoom,
  })

  const handleDoubleClickLabel = useCallback(() => {
    if (!w) return
    setRenameValue(w.label)
    setRenaming(true)
    setTimeout(() => renameRef.current?.select(), 0)
  }, [w])

  const commitRename = useCallback(() => {
    if (renameValue.trim()) {
      renameWindow(windowId, renameValue.trim())
    }
    setRenaming(false)
  }, [windowId, renameValue, renameWindow])

  if (!w) return null

  const TypeIcon = TYPE_ICONS[w.type]
  const clusterBorder = w.clusterId ? '3px solid var(--color-cyan)' : undefined

  if (w.maximized) {
    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 9999,
          background: 'var(--color-surface)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <WindowHeader
          w={w}
          TypeIcon={TypeIcon}
          renaming={renaming}
          renameValue={renameValue}
          renameRef={renameRef}
          setRenameValue={setRenameValue}
          commitRename={commitRename}
          handleDoubleClickLabel={handleDoubleClickLabel}
          toggleCollapse={() => toggleCollapse(windowId)}
          toggleMaximize={() => toggleMaximize(windowId)}
          togglePause={() => togglePause(windowId)}
          removeWindow={() => removeWindow(windowId)}
          popOut={() => popOut(windowId)}
          clusterBorder={clusterBorder}
        />
        <div className="flex-1 overflow-hidden">
          <WindowContent type={w.type} config={w.config} paused={w.paused} />
        </div>
      </div>
    )
  }

  if (w.poppedOut) {
    return (
      <div
        style={{
          position: 'absolute',
          left: w.x,
          top: w.y,
          width: w.width,
          height: 32,
          zIndex: w.zIndex,
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 6,
          opacity: 0.5,
          borderLeft: clusterBorder,
        }}
        className="flex items-center px-2 gap-1"
      >
        <TypeIcon size={12} style={{ color: 'var(--color-text-tertiary)' }} />
        <span className="text-[11px] truncate" style={{ color: 'var(--color-text-tertiary)' }}>
          Popped out — click to reclaim
        </span>
      </div>
    )
  }

  return (
    <div
      style={{
        position: 'absolute',
        left: w.x,
        top: w.y,
        width: w.width,
        height: w.collapsed ? 32 : w.height,
        zIndex: w.zIndex,
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 6,
        display: 'flex',
        flexDirection: 'column',
        borderLeft: clusterBorder,
      }}
      onPointerDown={() => bringToFront(windowId)}
    >
      {/* Resize handles */}
      {!w.collapsed &&
        RESIZE_EDGES.map(({ edge, style }) => (
          <div
            key={edge}
            style={{ position: 'absolute', zIndex: 10, ...style }}
            onPointerDown={(e) =>
              resize.onPointerDown(e, edge, {
                x: w.x,
                y: w.y,
                width: w.width,
                height: w.height,
              })
            }
            onPointerMove={resize.onPointerMove}
            onPointerUp={resize.onPointerUp}
          />
        ))}

      {/* Header */}
      <WindowHeader
        w={w}
        TypeIcon={TypeIcon}
        renaming={renaming}
        renameValue={renameValue}
        renameRef={renameRef}
        setRenameValue={setRenameValue}
        commitRename={commitRename}
        handleDoubleClickLabel={handleDoubleClickLabel}
        toggleCollapse={() => toggleCollapse(windowId)}
        toggleMaximize={() => toggleMaximize(windowId)}
        togglePause={() => togglePause(windowId)}
        removeWindow={() => removeWindow(windowId)}
        popOut={() => popOut(windowId)}
        clusterBorder={clusterBorder}
        dragHandlers={{
          onPointerDown: (e: React.PointerEvent) => drag.onPointerDown(e, w.x, w.y),
          onPointerMove: drag.onPointerMove,
          onPointerUp: drag.onPointerUp,
        }}
      />

      {/* Body */}
      {!w.collapsed && (
        <div className="flex-1 overflow-hidden" style={{ borderRadius: '0 0 5px 5px' }}>
          <WindowContent type={w.type} config={w.config} paused={w.paused} />
        </div>
      )}
    </div>
  )
}

// ── Header sub-component ─────────────────────────────────────

interface WindowHeaderProps {
  w: CanvasWindowType
  TypeIcon: typeof Globe
  renaming: boolean
  renameValue: string
  renameRef: React.RefObject<HTMLInputElement | null>
  setRenameValue: (v: string) => void
  commitRename: () => void
  handleDoubleClickLabel: () => void
  toggleCollapse: () => void
  toggleMaximize: () => void
  togglePause: () => void
  removeWindow: () => void
  popOut: () => void
  clusterBorder?: string
  dragHandlers?: {
    onPointerDown: (e: React.PointerEvent) => void
    onPointerMove: (e: React.PointerEvent) => void
    onPointerUp: (e: React.PointerEvent) => void
  }
}

function WindowHeader({
  w,
  TypeIcon,
  renaming,
  renameValue,
  renameRef,
  setRenameValue,
  commitRename,
  handleDoubleClickLabel,
  toggleCollapse,
  toggleMaximize,
  togglePause,
  removeWindow,
  popOut,
  dragHandlers,
}: WindowHeaderProps) {
  const btnStyle = { color: 'var(--color-text-tertiary)' }

  return (
    <div
      className="flex items-center gap-1 px-2 shrink-0 select-none"
      style={{
        height: 32,
        background: 'var(--color-surface-raised)',
        borderRadius: w.collapsed ? 5 : '5px 5px 0 0',
        borderBottom: w.collapsed ? undefined : '1px solid var(--color-border)',
        cursor: dragHandlers ? 'grab' : undefined,
      }}
      onPointerDown={dragHandlers?.onPointerDown}
      onPointerMove={dragHandlers?.onPointerMove}
      onPointerUp={dragHandlers?.onPointerUp}
    >
      {/* Connection dot */}
      <div
        className="w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: STATUS_COLORS[w.connectionStatus] }}
      />

      {/* Type icon */}
      <TypeIcon size={12} style={{ color: 'var(--color-text-tertiary)', flexShrink: 0 }} />

      {/* Label */}
      {renaming ? (
        <input
          ref={renameRef}
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onBlur={commitRename}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commitRename()
            if (e.key === 'Escape') {
              setRenameValue('')
              commitRename()
            }
            e.stopPropagation()
          }}
          className="flex-1 text-[11px] px-1 rounded outline-none min-w-0"
          style={{
            background: 'var(--color-surface)',
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-border-active)',
          }}
          onPointerDown={(e) => e.stopPropagation()}
        />
      ) : (
        <span
          className="flex-1 text-[11px] truncate"
          style={{ color: 'var(--color-text-primary)' }}
          onDoubleClick={handleDoubleClickLabel}
        >
          {w.label}
        </span>
      )}

      {/* Paused badge */}
      {w.paused && (
        <span
          className="text-[9px] px-1 rounded font-semibold shrink-0"
          style={{ background: 'var(--color-warn-dim)', color: 'var(--color-warn)' }}
        >
          PAUSED
        </span>
      )}

      {/* Badge count */}
      {w.badgeCount > 0 && (
        <span
          className="text-[9px] px-1 rounded-full font-semibold shrink-0"
          style={{ background: 'var(--color-cyan)', color: 'var(--color-text-inverse)' }}
        >
          {w.badgeCount}
        </span>
      )}

      {/* Action buttons */}
      <button
        onClick={(e) => { e.stopPropagation(); popOut() }}
        className="p-0.5 rounded hover:opacity-80"
        style={btnStyle}
        title="Pop out"
      >
        <ExternalLink size={11} />
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); toggleCollapse() }}
        className="p-0.5 rounded hover:opacity-80"
        style={btnStyle}
        title={w.collapsed ? 'Expand' : 'Collapse'}
      >
        {w.collapsed ? <ChevronDown size={11} /> : <ChevronUp size={11} />}
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); togglePause() }}
        className="p-0.5 rounded hover:opacity-80"
        style={btnStyle}
        title={w.paused ? 'Resume' : 'Pause'}
      >
        {w.paused ? <Play size={11} /> : <Pause size={11} />}
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); toggleMaximize() }}
        className="p-0.5 rounded hover:opacity-80"
        style={btnStyle}
        title={w.maximized ? 'Restore' : 'Maximize'}
      >
        {w.maximized ? <Minimize2 size={11} /> : <Maximize2 size={11} />}
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); removeWindow() }}
        className="p-0.5 rounded hover:opacity-80"
        style={{ color: 'var(--color-danger)' }}
        title="Close"
      >
        <X size={11} />
      </button>
    </div>
  )
}
