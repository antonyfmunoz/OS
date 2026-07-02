import { useCallback } from 'react'
import { useCockpitStore } from '../stores/cockpitStore'
import { RightRail } from './RightRail'

export function RightDrawer() {
  const open = useCockpitStore((s) => s.rightDrawerOpen)
  const toggle = useCockpitStore((s) => s.toggleRightDrawer)

  const handleBackdrop = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget) toggle()
  }, [toggle])

  return (
    <>
      {open && (
        <div
          className="absolute inset-0 z-30"
          style={{ background: 'rgba(0, 0, 0, 0.3)' }}
          onClick={handleBackdrop}
        />
      )}
      <div
        className="absolute top-0 right-0 h-full z-40 flex flex-col overflow-hidden"
        style={{
          width: 360,
          transform: open ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 200ms ease',
        }}
      >
        <RightRail />
      </div>
    </>
  )
}
