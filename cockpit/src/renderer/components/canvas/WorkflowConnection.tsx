import { useCallback } from 'react'
import type { WorkflowConnection as WfConnection, WorkflowNode } from '../../stores/workflowCanvasStore'

interface Props {
  connection: WfConnection
  nodes: WorkflowNode[]
  selected: boolean
  onSelect: (id: string) => void
}

function getPortPosition(
  node: WorkflowNode,
  role: 'output' | 'input',
  port: string,
): { x: number; y: number } {
  if (role === 'input') {
    return { x: node.x + node.width / 2, y: node.y }
  }
  if (port === 'true') {
    return { x: node.x + node.width / 3, y: node.y + node.height }
  }
  if (port === 'false') {
    return { x: node.x + (2 * node.width) / 3, y: node.y + node.height }
  }
  return { x: node.x + node.width / 2, y: node.y + node.height }
}

export function WorkflowConnection({ connection, nodes, selected, onSelect }: Props) {
  const fromNode = nodes.find((n) => n.id === connection.fromNodeId)
  const toNode = nodes.find((n) => n.id === connection.toNodeId)

  const handleClick = useCallback(
    (e: React.MouseEvent<SVGPathElement>) => {
      e.stopPropagation()
      onSelect(connection.id)
    },
    [onSelect, connection.id],
  )

  if (!fromNode || !toNode) return null

  const start = getPortPosition(fromNode, 'output', connection.fromPort)
  const end = getPortPosition(toNode, 'input', 'default')

  const dy = Math.abs(end.y - start.y)
  const offset = Math.max(60, dy * 0.4)

  const d = `M ${start.x} ${start.y} C ${start.x} ${start.y + offset}, ${end.x} ${end.y - offset}, ${end.x} ${end.y}`

  const markerRef = selected ? 'url(#wf-arrowhead-active)' : 'url(#wf-arrowhead)'
  const strokeColor = selected ? 'var(--color-cyan)' : 'var(--color-text-tertiary)'

  return (
    <g>
      {/* Invisible wide path for click target */}
      <path
        d={d}
        fill="none"
        stroke="transparent"
        strokeWidth={12}
        style={{ pointerEvents: 'stroke', cursor: 'pointer' }}
        onClick={handleClick}
      />
      {/* Visible path */}
      <path
        d={d}
        fill="none"
        stroke={strokeColor}
        strokeWidth={2}
        markerEnd={markerRef}
        style={{ pointerEvents: 'none' }}
      />
    </g>
  )
}
