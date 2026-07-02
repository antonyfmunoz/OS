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
      className="wv-card absolute left-2 z-20 flex flex-col overflow-hidden overflow-y-auto"
      style={{
        width: 160,
        top: 72,
        bottom: 112,
      }}
    >
      {children}
    </div>
  )
}
