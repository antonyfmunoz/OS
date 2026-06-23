interface ExecutorBadgeProps {
  executorType?: string
  targetMachine?: string
  className?: string
}

export function ExecutorBadge({ executorType, targetMachine, className = '' }: ExecutorBadgeProps) {
  if (!executorType) return null

  const isSimulation = executorType === 'simulation' || executorType === 'SimulationExecutor'
  const isLive = executorType === 'workstation' || executorType === 'agent' || executorType === 'WorkstationExecutor' || executorType === 'AgentExecutor'

  const label = isSimulation ? 'SIM' : isLive ? 'LIVE' : executorType.toUpperCase()
  const color = isSimulation ? 'var(--color-warn)' : isLive ? 'var(--color-ok)' : 'var(--color-text-tertiary)'
  const bg = isSimulation ? 'rgba(234, 179, 8, 0.1)' : isLive ? 'rgba(34, 197, 94, 0.1)' : 'rgba(107, 114, 128, 0.1)'

  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono ${className}`}
      style={{ color, background: bg, border: `1px solid ${color}40` }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      {label}
      {targetMachine && <span style={{ color: 'var(--color-text-tertiary)' }}>• {targetMachine}</span>}
    </span>
  )
}
