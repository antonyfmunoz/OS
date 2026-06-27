interface Props {
  paused: boolean
}

export function VisionWindowContent({ paused }: Props) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-2" style={{ color: 'var(--color-text-tertiary)' }}>
      <span className="text-[12px]">Vision Camera</span>
      <span className="text-[10px]">{paused ? 'Paused' : 'Connect via vision relay'}</span>
    </div>
  )
}
