import { useEffect, useRef, type ReactNode } from 'react'

interface DetailDrawerProps {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  badge?: ReactNode
  tabs?: string[]
  activeTab?: string
  onTabChange?: (tab: string) => void
  actions?: ReactNode
  children: ReactNode
}

export function DetailDrawer({
  open,
  onClose,
  title,
  subtitle,
  badge,
  tabs,
  activeTab,
  onTabChange,
  actions,
  children,
}: DetailDrawerProps) {
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (open) closeRef.current?.focus()
  }, [open])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  return (
    <>
      {open && (
        <div
          className="wv-drawer-overlay"
          data-testid="drawer-overlay"
          onClick={onClose}
        />
      )}
      <div
        className={`wv-drawer ${open ? 'open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        <div
          className="flex items-start justify-between gap-3 px-4 py-3"
          style={{ borderBottom: '1px solid var(--color-border)' }}
        >
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h2
                id="drawer-title"
                className="text-sm font-semibold truncate"
                style={{ color: 'var(--color-text-primary)' }}
              >
                {title}
              </h2>
              {badge}
            </div>
            {subtitle && (
              <p
                className="text-xs mt-0.5 truncate"
                style={{ color: 'var(--color-text-tertiary)' }}
              >
                {subtitle}
              </p>
            )}
          </div>
          <button
            ref={closeRef}
            onClick={onClose}
            aria-label="Close drawer"
            className="text-sm px-1.5 py-0.5 rounded"
            style={{
              color: 'var(--color-text-tertiary)',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            x
          </button>
        </div>

        {tabs && tabs.length > 0 && (
          <div
            className="flex gap-0 overflow-x-auto"
            style={{ borderBottom: '1px solid var(--color-border)' }}
          >
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => onTabChange?.(tab)}
                className="px-3 py-2 text-xs font-mono whitespace-nowrap"
                style={{
                  color:
                    activeTab === tab
                      ? 'var(--color-cyan)'
                      : 'var(--color-text-tertiary)',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: `2px solid ${activeTab === tab ? 'var(--color-cyan)' : 'transparent'}`,
                  cursor: 'pointer',
                }}
              >
                {tab}
              </button>
            ))}
          </div>
        )}

        {actions && (
          <div
            className="flex items-center gap-2 px-4 py-2"
            style={{ borderBottom: '1px solid var(--color-border)' }}
          >
            {actions}
          </div>
        )}

        <div className="px-4 py-3 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 120px)' }}>
          {children}
        </div>
      </div>
    </>
  )
}
