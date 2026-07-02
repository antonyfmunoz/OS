import { type ReactNode } from 'react'
import { useCockpitStore } from '../stores/cockpitStore'

interface LeftDrawerProps {
  children: ReactNode
}

export function LeftDrawer({ children }: LeftDrawerProps) {
  const open = useCockpitStore((s) => s.leftDrawerOpen)

  if (!open) return null

  return (
    <div
      className="wv-card absolute left-2 z-20 flex flex-col overflow-hidden"
      style={{
        width: 220,
        top: 48,
        bottom: 52,
      }}
    >
      {children}
    </div>
  )
}
