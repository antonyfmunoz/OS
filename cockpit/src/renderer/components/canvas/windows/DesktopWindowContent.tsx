import { Monitor } from 'lucide-react'

interface Props {
  monitorId?: string
  paused: boolean
}

export function DesktopWindowContent({ monitorId, paused }: Props) {
  const id = monitorId ?? 'M0'
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3"
      style={{ color: 'var(--color-text-tertiary)' }}>
      <Monitor size={24} />
      <span className="text-[12px] font-medium" style={{ color: 'var(--color-text-secondary)' }}>
        Desktop {id}
      </span>
      <span className="text-[10px]">
        {paused ? 'Paused' : 'Desktop relay not available'}
      </span>
      <span className="text-[9px] px-3 text-center" style={{ maxWidth: 200 }}>
        Requires desktop streaming service on executor node
      </span>
    </div>
  )
}
