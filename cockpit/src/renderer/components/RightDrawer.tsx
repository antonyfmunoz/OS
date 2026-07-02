import { useCockpitStore } from '../stores/cockpitStore'
import { RightRail } from './RightRail'

export function RightDrawer() {
  const open = useCockpitStore((s) => s.rightDrawerOpen)

  if (!open) return null

  return (
    <div
      className="wv-card absolute right-2 z-20 flex flex-col overflow-hidden"
      style={{
        width: 360,
        top: 48,
        bottom: 52,
      }}
    >
      <RightRail />
    </div>
  )
}
