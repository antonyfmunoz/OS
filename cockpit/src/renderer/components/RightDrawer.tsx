import { useCockpitStore } from '../stores/cockpitStore'
import { useIsMobile } from '../hooks/useIsMobile'
import { RightRail } from './RightRail'

export function RightDrawer() {
  const open = useCockpitStore((s) => s.rightDrawerOpen)
  const mobile = useIsMobile()

  if (!open) return null

  return (
    <div
      className="wv-card absolute z-20 flex flex-col overflow-hidden"
      style={{
        width: mobile ? 'calc(100% - 12px)' : 160,
        right: 6,
        top: 48,
        bottom: 48,
        ...(mobile ? { left: 6 } : {}),
      }}
    >
      <RightRail />
    </div>
  )
}
