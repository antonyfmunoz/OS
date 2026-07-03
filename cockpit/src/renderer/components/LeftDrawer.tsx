import { type ReactNode } from 'react'
import { useCockpitStore } from '../stores/cockpitStore'
import { useIsMobile } from '../hooks/useIsMobile'

interface LeftDrawerProps {
  children: ReactNode
}

export function LeftDrawer({ children }: LeftDrawerProps) {
  const open = useCockpitStore((s) => s.leftDrawerOpen)
  const mobile = useIsMobile()

  if (!open) return null

  return (
    <div
      className="wv-card absolute z-20 flex flex-col overflow-hidden overflow-y-auto"
      style={{
        width: mobile ? 'calc(33vw)' : 160,
        left: 6,
        top: mobile ? 80 : 6,
        bottom: mobile ? 78 : 36,
      }}
    >
      {children}
    </div>
  )
}
