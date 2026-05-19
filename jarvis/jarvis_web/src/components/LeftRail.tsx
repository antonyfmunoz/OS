import { clsx } from 'clsx'
import { ChevronLeft, ChevronRight, Radio } from 'lucide-react'
import { useCockpitStore } from '../stores/cockpitStore.ts'
import { ROUTES, ROUTE_GROUPS } from '../types/routes.ts'

export function LeftRail() {
  const { route, railCollapsed, wsConnected, setRoute, toggleRail } = useCockpitStore()

  return (
    <nav
      className={clsx(
        'flex flex-col h-full bg-surface border-r border-border transition-all duration-200 select-none',
        railCollapsed ? 'w-[var(--spacing-rail-collapsed)]' : 'w-[var(--spacing-rail)]',
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-border">
        {!railCollapsed && (
          <div className="flex items-center gap-2">
            <div className={clsx('w-2 h-2 rounded-full', wsConnected ? 'bg-ok wv-pulse' : 'bg-danger')} />
            <span className="text-[11px] font-mono text-text-secondary tracking-wider uppercase">
              UMH Cockpit
            </span>
          </div>
        )}
        <button onClick={toggleRail} className="p-1 text-text-tertiary hover:text-cyan transition-colors">
          {railCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Route groups */}
      <div className="flex-1 overflow-y-auto py-2">
        {ROUTE_GROUPS.map((group) => {
          const groupRoutes = ROUTES.filter((r) => r.group === group.key)
          return (
            <div key={group.key} className="mb-2">
              {!railCollapsed && (
                <div className="px-4 py-1 wv-label">{group.label}</div>
              )}
              {groupRoutes.map((r) => {
                const Icon = r.icon
                const active = route === r.id
                return (
                  <button
                    key={r.id}
                    onClick={() => setRoute(r.id)}
                    className={clsx(
                      'flex items-center gap-3 w-full px-3 py-1.5 text-left transition-colors',
                      active
                        ? 'text-cyan bg-cyan-glow border-r-2 border-cyan'
                        : 'text-text-secondary hover:text-text-primary hover:bg-surface-raised',
                    )}
                    title={railCollapsed ? r.label : undefined}
                  >
                    <Icon size={16} className={active ? 'text-cyan' : ''} />
                    {!railCollapsed && (
                      <span className="text-[12px] font-mono truncate">{r.label}</span>
                    )}
                  </button>
                )
              })}
            </div>
          )
        })}
      </div>

      {/* Presence indicator */}
      <div className="px-3 py-2 border-t border-border">
        <div className="flex items-center gap-2">
          <Radio size={12} className="text-cyan wv-pulse" />
          {!railCollapsed && (
            <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
              Full-Screen
            </span>
          )}
        </div>
      </div>
    </nav>
  )
}
