import { useState, useCallback, lazy, Suspense } from 'react'
import { Bot, Minus, Maximize2, Minimize2, X } from 'lucide-react'
import { useCanvasDrag } from '../../hooks/useCanvasDrag'
import { useAgentCanvasStore, type AgentCanvasNode as NodeType } from '../../stores/agentCanvasStore'
import { AgentWindowContent } from './windows/AgentWindowContent'

const AgentConfigView = lazy(() =>
  import('./windows/AgentConfigView').then((m) => ({ default: m.AgentConfigView })),
)

interface Props {
  node: NodeType
  zoom: number
  onDismiss: (agentId: string) => void
}

export function AgentCanvasNode({ node, zoom, onDismiss }: Props) {
  const updateNode = useAgentCanvasStore((s) => s.updateNode)
  const bringToFront = useAgentCanvasStore((s) => s.bringToFront)
  const toggleCollapse = useAgentCanvasStore((s) => s.toggleCollapse)
  const toggleMaximize = useAgentCanvasStore((s) => s.toggleMaximize)

  const [dragPos, setDragPos] = useState<{ x: number; y: number } | null>(null)

  const { onPointerDown, onPointerMove, onPointerUp } = useCanvasDrag({
    zoom,
    onDrag: (x, y) => setDragPos({ x, y }),
    onDragEnd: (x, y) => {
      setDragPos(null)
      updateNode(node.agentId, { x, y })
    },
  })

  const handleClick = useCallback(() => bringToFront(node.agentId), [bringToFront, node.agentId])

  const x = dragPos?.x ?? node.x
  const y = dragPos?.y ?? node.y

  if (node.maximized) {
    return (
      <Suspense fallback={
        <div className="fixed inset-0 z-[9999] flex items-center justify-center" style={{ background: 'var(--color-surface)' }}>
          <span className="text-[12px]" style={{ color: 'var(--color-text-tertiary)' }}>Loading config view...</span>
        </div>
      }>
        <div className="fixed inset-0 z-[9999]" style={{ background: 'var(--color-surface)' }}>
          <div className="flex items-center gap-2 px-3 h-8 shrink-0" style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-surface-raised)' }}>
            <Bot size={14} style={{ color: 'var(--color-text-tertiary)' }} />
            <span className="text-[12px] font-medium" style={{ color: 'var(--color-text-primary)' }}>{node.label}</span>
            <div className="flex-1" />
            <button onClick={() => toggleMaximize(node.agentId)} className="p-1 rounded hover:opacity-80" style={{ color: 'var(--color-text-tertiary)' }} title="Exit config view">
              <Minimize2 size={14} />
            </button>
          </div>
          <div className="h-[calc(100%-32px)]">
            <AgentConfigView agentId={node.agentId} onClose={() => toggleMaximize(node.agentId)} />
          </div>
        </div>
      </Suspense>
    )
  }

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: node.width,
        height: node.collapsed ? 32 : node.height,
        zIndex: node.zIndex,
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 6,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
      onClick={handleClick}
    >
      {/* Header */}
      <div
        className="flex items-center gap-1.5 px-2 shrink-0 select-none"
        style={{ height: 32, background: 'var(--color-surface-raised)', cursor: 'grab', borderBottom: node.collapsed ? 'none' : '1px solid var(--color-border)' }}
        onPointerDown={(e) => onPointerDown(e, node.x, node.y)}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      >
        <Bot size={12} style={{ color: 'var(--color-text-tertiary)' }} />
        <span className="text-[11px] font-medium truncate flex-1" style={{ color: 'var(--color-text-primary)' }}>
          {node.label}
        </span>

        <button onClick={(e) => { e.stopPropagation(); toggleCollapse(node.agentId) }} className="p-0.5 rounded hover:opacity-80" style={{ color: 'var(--color-text-tertiary)' }}>
          <Minus size={12} />
        </button>
        <button onClick={(e) => { e.stopPropagation(); toggleMaximize(node.agentId) }} className="p-0.5 rounded hover:opacity-80" style={{ color: 'var(--color-text-tertiary)' }} title="Open config view">
          <Maximize2 size={12} />
        </button>
        <button onClick={(e) => { e.stopPropagation(); onDismiss(node.agentId) }} className="p-0.5 rounded hover:opacity-80" style={{ color: 'var(--color-text-tertiary)' }}>
          <X size={12} />
        </button>
      </div>

      {/* Body */}
      {!node.collapsed && (
        <div className="flex-1 overflow-hidden">
          <AgentWindowContent agentId={node.agentId} paused={false} />
        </div>
      )}
    </div>
  )
}
