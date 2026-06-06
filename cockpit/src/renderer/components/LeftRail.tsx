import { clsx } from 'clsx'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useCockpitStore } from '../stores/cockpitStore'
import { ROUTES, ROUTE_GROUPS } from '../types/routes'

export function LeftRail() {
  const activePanel = useCockpitStore((s) => s.activePanel)
  const railCollapsed = useCockpitStore((s) => s.railCollapsed)
  const setPanel = useCockpitStore((s) => s.setPanel)
  const toggleRail = useCockpitStore((s) => s.toggleRail)

  return (
    <nav
      className={clsx(
        'flex flex-col h-full bg-surface border-r border-border transition-all duration-200 select-none',
        railCollapsed ? 'w-[var(--spacing-rail-collapsed)]' : 'w-[var(--spacing-rail)]',
      )}
    >
      {/* Collapse toggle — matches RightRail h-9 */}
      <div className="flex items-center justify-end px-2 h-9 shrink-0 border-b border-border">
        <button onClick={toggleRail} className="p-1 text-text-tertiary hover:text-cyan transition-colors">
          {railCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Route groups */}
      <div className="flex-1 overflow-y-auto py-2">
        {ROUTE_GROUPS.map((group) => {
          const groupRoutes = ROUTES.filter(
            (r) => r.group === group.key && (r.visibility === 'primary' || r.visibility === 'system'),
          )
          return (
            <div key={group.key} className="mb-2">
              {!railCollapsed && (
                <div className="px-4 py-1 wv-label">{group.label}</div>
              )}
              {groupRoutes.map((r) => {
                const Icon = r.icon
                const active = activePanel === r.id
                return (
                  <button
                    key={r.id}
                    onClick={() => setPanel(r.id)}
                    className={clsx(
                      'flex items-center gap-3 w-full px-3 py-1.5 text-left transition-colors',
                      active
                        ? 'text-cyan bg-cyan-glow border-r-2 border-cyan'
                        : 'text-text-secondary hover:text-text-primary hover:bg-surface-raised',
                    )}
                    title={railCollapsed ? `${r.label} (Ctrl+${r.key})` : undefined}
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
    </nav>
  )
}
