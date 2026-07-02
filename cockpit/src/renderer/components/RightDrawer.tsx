import { useCockpitStore } from '../stores/cockpitStore'
import { RightRail } from './RightRail'

export function RightDrawer() {
  const open = useCockpitStore((s) => s.rightDrawerOpen)

  if (!open) return null

  return (
    <div
      className="wv-card absolute z-20 flex flex-col overflow-hidden"
      style={{
        width: 240,
        right: 6,
        top: 12,
        bottom: 78,
      }}
    >
      <RightRail />
    </div>
  )
}
