interface RingGaugeProps {
  value: number
  max: number
  label: string
  unit?: string
  color?: string
  size?: number
}

export function RingGauge({ value, max, label, unit = '', color = 'var(--accent-cyan)', size = 80 }: RingGaugeProps) {
  const pct = Math.min(value / Math.max(max, 1), 1)
  const radius = (size - 8) / 2
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference * (1 - pct)

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border-focus)"
          strokeWidth={3}
        />
        {/* Value ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={3}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-500 ease-out"
          style={{ filter: `drop-shadow(0 0 4px ${color}40)` }}
        />
      </svg>
      <div className="text-center -mt-[calc(50%+8px)] mb-4">
        <span className="font-mono text-lg font-semibold" style={{ color }}>
          {typeof value === 'number' ? (value % 1 === 0 ? value : value.toFixed(1)) : value}
        </span>
        {unit && <span className="text-xs ml-0.5" style={{ color: 'var(--text-tertiary)' }}>{unit}</span>}
      </div>
      <span className="hud-text text-center">{label}</span>
    </div>
  )
}
