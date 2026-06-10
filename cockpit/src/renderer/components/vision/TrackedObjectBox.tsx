interface TrackedObjectBoxProps {
  x: number
  y: number
  w: number
  h: number
  label: string
  confidence: number
  color?: string
}

export function TrackedObjectBox({ x, y, w, h, label, confidence, color = '#22c55e' }: TrackedObjectBoxProps) {
  return (
    <g>
      <rect
        x={x} y={y} width={w} height={h}
        fill="none" stroke={color} strokeWidth={2}
        rx={2} ry={2} opacity={0.8}
      />
      {label && (
        <>
          <rect
            x={x} y={y - 16} width={Math.max(w, 60)} height={16}
            fill={color} opacity={0.7} rx={2} ry={2}
          />
          <text
            x={x + 3} y={y - 4}
            fill="white" fontSize={11} fontFamily="monospace"
          >
            {label} {Math.round(confidence * 100)}%
          </text>
        </>
      )}
    </g>
  )
}
