import { useState, useCallback } from 'react'
import { Play, Zap, GitBranch, Shield, Clock, GitMerge, Bell, Square } from 'lucide-react'
import { useCanvasDrag } from '../../hooks/useCanvasDrag'
import type { WorkflowNode as WfNode } from '../../stores/workflowCanvasStore'

// ── Color + icon mapping ───────────────────────────────────────

const STEP_COLORS: Record<string, string> = {
  trigger: '#22c55e',
  action: '#3b82f6',
  decision: '#f59e0b',
  approval_gate: '#a855f7',
  wait: '#6b7280',
  parallel: '#14b8a6',
  notification: '#ec4899',
  end: '#ef4444',
}

const STEP_ICONS: Record<string, React.ReactNode> = {
  trigger: <Play size={12} />,
  action: <Zap size={12} />,
  decision: <GitBranch size={12} />,
  approval_gate: <Shield size={12} />,
  wait: <Clock size={12} />,
  parallel: <GitMerge size={12} />,
  notification: <Bell size={12} />,
  end: <Square size={12} />,
}

const PORT_SIZE = 8

// ── Component ──────────────────────────────────────────────────

interface Props {
  node: WfNode
  zoom: number
  selected: boolean
  onSelect: (id: string) => void
  onMove: (id: string, x: number, y: number) => void
}

export function WorkflowNode({ node, zoom, selected, onSelect, onMove }: Props) {
  const [dragPos, setDragPos] = useState<{ x: number; y: number } | null>(null)
  const [editing, setEditing] = useState(false)
  const [editLabel, setEditLabel] = useState(node.label)

  const { onPointerDown, onPointerMove, onPointerUp } = useCanvasDrag({
    zoom,
    onDrag: (x, y) => setDragPos({ x, y }),
    onDragEnd: (x, y) => {
      setDragPos(null)
      onMove(node.id, x, y)
    },
  })

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onSelect(node.id)
    },
    [onSelect, node.id],
  )

  const handleDoubleClick = useCallback(() => {
    setEditLabel(node.label)
    setEditing(true)
  }, [node.label])

  const commitLabel = useCallback(() => {
    setEditing(false)
  }, [])

  const color = STEP_COLORS[node.stepType] ?? '#6b7280'
  const icon = STEP_ICONS[node.stepType]
  const isRounded = node.stepType === 'trigger' || node.stepType === 'end'
  const isDecision = node.stepType === 'decision'

  const x = dragPos?.x ?? node.x
  const y = dragPos?.y ?? node.y

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: node.width,
        height: node.height,
        background: 'var(--color-surface)',
        border: selected
          ? '2px solid var(--color-cyan)'
          : '1px solid var(--color-border)',
        borderRadius: isRounded ? 8 : 6,
        overflow: 'visible',
        cursor: 'grab',
        display: 'flex',
        flexDirection: 'column',
      }}
      onClick={handleClick}
      onPointerDown={(e) => onPointerDown(e, node.x, node.y)}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
    >
      {/* Color bar */}
      <div
        style={{
          height: 4,
          background: color,
          borderRadius: isRounded ? '6px 6px 0 0' : '4px 4px 0 0',
          flexShrink: 0,
        }}
      />

      {/* Header */}
      <div
        className="flex items-center gap-1.5 px-2 py-1"
        style={{ flexShrink: 0 }}
      >
        <span style={{ color }}>{icon}</span>
        {editing ? (
          <input
            autoFocus
            value={editLabel}
            onChange={(e) => setEditLabel(e.target.value)}
            onBlur={commitLabel}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitLabel()
              if (e.key === 'Escape') { setEditing(false); setEditLabel(node.label) }
            }}
            className="flex-1 text-[11px] px-1 py-0 rounded"
            style={{
              background: 'var(--color-canvas)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border)',
              outline: 'none',
              fontFamily: 'var(--font-sans)',
            }}
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span
            className="text-[11px] font-medium truncate flex-1"
            style={{ color: 'var(--color-text-primary)' }}
            onDoubleClick={handleDoubleClick}
          >
            {node.label}
          </span>
        )}
      </div>

      {/* Body */}
      {node.stepType !== 'trigger' && node.stepType !== 'end' && (
        <div className="px-2 pb-1.5 flex flex-col gap-0.5" style={{ flexShrink: 0 }}>
          {node.config.executionMode && (
            <span
              className="inline-flex self-start px-1.5 py-0.5 rounded text-[9px] uppercase tracking-wider"
              style={{
                background: `${color}22`,
                color,
              }}
            >
              {node.config.executionMode}
            </span>
          )}
          {node.config.actionType && (
            <span
              className="text-[10px] truncate"
              style={{ color: 'var(--color-text-tertiary)' }}
            >
              {node.config.actionType}
            </span>
          )}
        </div>
      )}

      {/* Input port — top center (hidden for trigger) */}
      {node.stepType !== 'trigger' && (
        <div
          style={{
            position: 'absolute',
            top: -PORT_SIZE / 2,
            left: node.width / 2 - PORT_SIZE / 2,
            width: PORT_SIZE,
            height: PORT_SIZE,
            borderRadius: '50%',
            background: 'var(--color-surface-raised)',
            border: '2px solid var(--color-border)',
          }}
        />
      )}

      {/* Output port(s) — bottom (hidden for end) */}
      {node.stepType !== 'end' && !isDecision && (
        <div
          style={{
            position: 'absolute',
            bottom: -PORT_SIZE / 2,
            left: node.width / 2 - PORT_SIZE / 2,
            width: PORT_SIZE,
            height: PORT_SIZE,
            borderRadius: '50%',
            background: 'var(--color-surface-raised)',
            border: `2px solid ${color}`,
          }}
        />
      )}

      {/* Decision: two output ports */}
      {isDecision && (
        <>
          <div
            style={{
              position: 'absolute',
              bottom: -PORT_SIZE / 2,
              left: node.width / 3 - PORT_SIZE / 2,
              width: PORT_SIZE,
              height: PORT_SIZE,
              borderRadius: '50%',
              background: '#22c55e',
              border: '2px solid #22c55e',
            }}
            title="True"
          />
          <span
            className="text-[8px] absolute"
            style={{
              bottom: -PORT_SIZE - 10,
              left: node.width / 3 - 8,
              color: '#22c55e',
            }}
          >
            T
          </span>
          <div
            style={{
              position: 'absolute',
              bottom: -PORT_SIZE / 2,
              left: (2 * node.width) / 3 - PORT_SIZE / 2,
              width: PORT_SIZE,
              height: PORT_SIZE,
              borderRadius: '50%',
              background: '#ef4444',
              border: '2px solid #ef4444',
            }}
            title="False"
          />
          <span
            className="text-[8px] absolute"
            style={{
              bottom: -PORT_SIZE - 10,
              left: (2 * node.width) / 3 - 4,
              color: '#ef4444',
            }}
          >
            F
          </span>
        </>
      )}
    </div>
  )
}
