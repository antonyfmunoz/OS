interface Landmark {
  x: number
  y: number
  label?: string
}

interface PoseSkeletonOverlayProps {
  landmarks: Landmark[]
  connections: Array<[number, number]>
  color?: string
}

export function PoseSkeletonOverlay({ landmarks, connections, color = '#a78bfa' }: PoseSkeletonOverlayProps) {
  if (landmarks.length === 0) return null

  return (
    <g>
      {connections.map(([a, b], i) => {
        const la = landmarks[a]
        const lb = landmarks[b]
        if (!la || !lb) return null
        return (
          <line
            key={`s-${i}`}
            x1={la.x} y1={la.y} x2={lb.x} y2={lb.y}
            stroke={color} strokeWidth={2} opacity={0.7}
          />
        )
      })}
      {landmarks.map((lm, i) => (
        <circle
          key={`p-${i}`}
          cx={lm.x} cy={lm.y} r={4}
          fill={color} stroke="white" strokeWidth={1} opacity={0.9}
        />
      ))}
    </g>
  )
}
