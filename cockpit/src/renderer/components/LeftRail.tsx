import { clsx } from 'clsx'
import { ChevronLeft, ChevronRight, Radio } from 'lucide-react'
import { useCockpitStore } from '../stores/cockpitStore'
import { ROUTES, ROUTE_GROUPS } from '../types/routes'

export function LeftRail() {
  const activePanel = useCockpitStore((s) => s.activePanel)
  const railCollapsed = useCockpitStore((s) => s.railCollapsed)
  const wsStatus = useCockpitStore((s) => s.wsStatus)
  const apiStatus = useCockpitStore((s) => s.apiStatus)
  const setPanel = useCockpitStore((s) => s.setPanel)
  const toggleRail = useCockpitStore((s) => s.toggleRail)

  const isOnline = wsStatus === 'connected' || apiStatus === 'connected'

  return (
    <nav
      className={clsx(
        'flex flex-col h-full bg-surface border-r border-border transition-all duration-200 select-none',
        railCollapsed ? 'w-[var(--spacing-rail-collapsed)]' : 'w-[var(--spacing-rail)]',
      )}
    >
      {/* Collapse toggle */}
      <div className="flex items-center justify-end px-3 py-3 border-b border-border">
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

      {/* Footer — fullscreen + connection status */}
      <div className="px-3 py-2 border-t border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radio size={12} className="text-cyan wv-pulse" />
            {!railCollapsed && (
              <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
                Full-Screen
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <div className={clsx('w-2 h-2 rounded-full', isOnline ? 'bg-ok wv-pulse' : 'bg-danger')} />
            {!railCollapsed && (
              <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
                {isOnline ? 'Online' : 'Offline'}
              </span>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
