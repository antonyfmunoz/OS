import { useCallback, type ReactNode } from 'react'
import { useCockpitStore } from '../stores/cockpitStore'

interface LeftDrawerProps {
  children: ReactNode
}

export function LeftDrawer({ children }: LeftDrawerProps) {
  const open = useCockpitStore((s) => s.leftDrawerOpen)
  const toggle = useCockpitStore((s) => s.toggleLeftDrawer)

  const handleBackdrop = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget) toggle()
  }, [toggle])

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40"
          style={{ background: 'rgba(0, 0, 0, 0.3)' }}
          onClick={handleBackdrop}
        />
      )}
      <div
        className="fixed left-0 z-40 flex flex-col overflow-hidden"
        style={{
          width: 220,
          top: 'var(--spacing-titlebar-height)',
          bottom: 'var(--spacing-hud-height)',
          background: 'var(--color-surface)',
          borderRight: '1px solid var(--color-border)',
          transform: open ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 200ms ease',
        }}
      >
        {children}
      </div>
    </>
  )
}
