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
        // Mobile: the chat rail's content (bubbles, composer + mic/attach
        // buttons, action chips) is sized for a ~240px rail. 55vw squeezed it
        // to ~half the phone, so it overflowed and read as zoomed-in with
        // horizontal scroll. Give it nearly the full width on mobile, with a
        // small gutter on each side; keep the fixed 240px rail on desktop.
        width: mobile ? undefined : 240,
        left: mobile ? 8 : undefined,
        right: mobile ? 8 : 6,
        top: mobile ? 80 : 6,
        bottom: mobile ? 78 : 36,
      }}
    >
      <RightRail />
    </div>
  )
}
