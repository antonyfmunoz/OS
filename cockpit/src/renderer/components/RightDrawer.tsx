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
        width: 160,
        right: 6,
        top: mobile ? '50%' : 52,
        bottom: 78,
      }}
    >
      <RightRail />
    </div>
  )
}
