interface Landmark {
  x: number
  y: number
  label?: string
}

interface FaceTrackingOverlayProps {
  x: number
  y: number
  w: number
  h: number
  label: string
  confidence: number
  landmarks?: Landmark[]
}

export function FaceTrackingOverlay({ x, y, w, h, label, confidence, landmarks }: FaceTrackingOverlayProps) {
  const color = '#3b82f6'

  return (
    <g>
      <rect
        x={x} y={y} width={w} height={h}
        fill="none" stroke={color} strokeWidth={2}
        rx={4} ry={4} opacity={0.8}
      />
      {label && (
        <>
          <rect
            x={x} y={y - 16} width={Math.max(w, 80)} height={16}
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
      {landmarks?.map((lm, i) => (
        <circle
          key={i}
          cx={lm.x} cy={lm.y} r={2}
          fill={color} opacity={0.9}
        />
      ))}
    </g>
  )
}
