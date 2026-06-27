interface Props {
  monitorId?: string
  paused: boolean
}

export function DesktopWindowContent({ monitorId, paused }: Props) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-2" style={{ color: 'var(--color-text-tertiary)' }}>
      <span className="text-[12px]">Desktop: {monitorId ?? 'M0'}</span>
      <span className="text-[10px]">{paused ? 'Paused' : 'Stream not connected — desktop relay required'}</span>
    </div>
  )
}
