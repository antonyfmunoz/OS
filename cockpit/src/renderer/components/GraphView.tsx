import { useEffect, useRef } from 'react'

interface GraphNode {
  id: string
  label: string
  type: string
  x?: number
  y?: number
  vx?: number
  vy?: number
}

interface GraphEdge {
  source: string
  target: string
  type: string
}

interface GraphViewProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  onNodeClick?: (node: GraphNode) => void
  colorMap?: Record<string, string>
}

export function GraphView({ nodes, edges, onNodeClick, colorMap = {} }: GraphViewProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const simRef = useRef<GraphNode[]>([])

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return

    const svg = svgRef.current
    const rect = svg.getBoundingClientRect()
    const w = rect.width || 600
    const h = rect.height || 400
    const cx = w / 2
    const cy = h / 2

    const simNodes = nodes.map((n, i) => ({
      ...n,
      x: n.x ?? cx + (Math.random() - 0.5) * w * 0.6,
      y: n.y ?? cy + (Math.random() - 0.5) * h * 0.6,
      vx: 0,
      vy: 0,
    }))
    simRef.current = simNodes

    const nodeMap = new Map(simNodes.map((n) => [n.id, n]))

    let frame: number
    let steps = 0
    const maxSteps = 200

    function tick() {
      const alpha = 1 - steps / maxSteps
      if (alpha <= 0) return

      for (const node of simNodes) {
        let fx = (cx - (node.x ?? 0)) * 0.01
        let fy = (cy - (node.y ?? 0)) * 0.01

        for (const other of simNodes) {
          if (other.id === node.id) continue
          const dx = (node.x ?? 0) - (other.x ?? 0)
          const dy = (node.y ?? 0) - (other.y ?? 0)
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          if (dist < 120) {
            const force = (120 - dist) / dist * 0.5
            fx += dx * force / dist
            fy += dy * force / dist
          }
        }

        for (const edge of edges) {
          const src = edge.source === node.id ? node : nodeMap.get(edge.source)
          const tgt = edge.target === node.id ? node : nodeMap.get(edge.target)
          if (src && tgt && (src.id === node.id || tgt.id === node.id)) {
            const other = src.id === node.id ? tgt : src
            const dx = (other.x ?? 0) - (node.x ?? 0)
            const dy = (other.y ?? 0) - (node.y ?? 0)
            const dist = Math.sqrt(dx * dx + dy * dy) || 1
            const desired = 100
            const force = (dist - desired) * 0.003
            fx += dx * force / dist
            fy += dy * force / dist
          }
        }

        node.vx = ((node.vx ?? 0) + fx) * 0.6
        node.vy = ((node.vy ?? 0) + fy) * 0.6
        node.x = (node.x ?? 0) + (node.vx ?? 0) * alpha
        node.y = (node.y ?? 0) + (node.vy ?? 0) * alpha
      }

      steps++
      simRef.current = [...simNodes]
      renderFrame()
      if (steps < maxSteps) frame = requestAnimationFrame(tick)
    }

    function renderFrame() {
      if (!svgRef.current) return
      const nodeEls = svgRef.current.querySelectorAll<SVGCircleElement>('[data-node-id]')
      const labelEls = svgRef.current.querySelectorAll<SVGTextElement>('[data-label-id]')
      const lineEls = svgRef.current.querySelectorAll<SVGLineElement>('[data-edge-idx]')

      nodeEls.forEach((el) => {
        const node = nodeMap.get(el.dataset.nodeId ?? '')
        if (node) {
          el.setAttribute('cx', String(node.x ?? 0))
          el.setAttribute('cy', String(node.y ?? 0))
        }
      })

      labelEls.forEach((el) => {
        const node = nodeMap.get(el.dataset.labelId ?? '')
        if (node) {
          el.setAttribute('x', String(node.x ?? 0))
          el.setAttribute('y', String((node.y ?? 0) + 20))
        }
      })

      lineEls.forEach((el) => {
        const idx = parseInt(el.dataset.edgeIdx ?? '0')
        const edge = edges[idx]
        if (edge) {
          const src = nodeMap.get(edge.source)
          const tgt = nodeMap.get(edge.target)
          if (src && tgt) {
            el.setAttribute('x1', String(src.x ?? 0))
            el.setAttribute('y1', String(src.y ?? 0))
            el.setAttribute('x2', String(tgt.x ?? 0))
            el.setAttribute('y2', String(tgt.y ?? 0))
          }
        }
      })
    }

    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [nodes, edges, colorMap])

  const defaultColor = 'var(--accent-cyan)'

  return (
    <svg
      ref={svgRef}
      className="w-full h-full"
      style={{ background: 'transparent' }}
    >
      {edges.map((edge, i) => (
        <line
          key={`e-${i}`}
          data-edge-idx={i}
          stroke="var(--border)"
          strokeWidth={1}
          opacity={0.4}
        />
      ))}
      {nodes.map((node) => (
        <g key={node.id}>
          <circle
            data-node-id={node.id}
            r={6}
            fill={colorMap[node.type] || defaultColor}
            opacity={0.8}
            style={{ cursor: onNodeClick ? 'pointer' : 'default' }}
            onClick={() => onNodeClick?.(node)}
          />
          <text
            data-label-id={node.id}
            textAnchor="middle"
            fontSize={9}
            fill="var(--text-tertiary)"
          >
            {node.label.length > 20 ? node.label.slice(0, 20) + '...' : node.label}
          </text>
        </g>
      ))}
    </svg>
  )
}
