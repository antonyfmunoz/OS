import { clsx } from 'clsx'
import { ChevronLeft, ChevronRight, Compass } from 'lucide-react'
import { useCockpitStore } from '../stores/cockpitStore'
import { ROUTES, ROUTE_GROUPS } from '../types/routes'

export function LeftRail() {
  const activePanel = useCockpitStore((s) => s.activePanel)
  const railCollapsed = useCockpitStore((s) => s.railCollapsed)
  const setPanel = useCockpitStore((s) => s.setPanel)
  const toggleRail = useCockpitStore((s) => s.toggleRail)

  const allRoutes = ROUTE_GROUPS.flatMap((group) =>
    ROUTES.filter((r) => r.group === group.key && (r.visibility === 'primary' || r.visibility === 'system')),
  )

  if (railCollapsed) {
    return (
      <nav className="flex flex-col items-center py-2 w-10 bg-surface border-r border-border select-none">
        <button onClick={toggleRail} className="p-1 text-text-tertiary hover:text-cyan">
          <ChevronRight size={14} />
        </button>
        {allRoutes.map((r) => {
          const Icon = r.icon
          return (
            <button
              key={r.id}
              onClick={() => { toggleRail(); setPanel(r.id) }}
              className={clsx('p-2 mt-1', activePanel === r.id ? 'text-cyan' : 'text-text-tertiary hover:text-text-secondary')}
              title={r.label}
            >
              <Icon size={14} />
            </button>
          )
        })}
      </nav>
    )
  }

  return (
    <nav className="flex flex-col h-full w-[var(--spacing-rail)] bg-surface border-r border-border select-none">
      {/* Header — matches RightRail h-9 style */}
      <div className="flex items-center border-b border-border px-2 h-9 shrink-0">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Compass size={14} className="text-cyan shrink-0" />
          <span className="text-[10px] font-mono text-cyan uppercase tracking-wider leading-none truncate">Navigation</span>
        </div>
        <button onClick={toggleRail} className="p-1 text-text-tertiary hover:text-cyan transition-colors shrink-0">
          <ChevronLeft size={14} />
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
              <div className="px-4 py-1 wv-label">{group.label}</div>
              {groupRoutes.map((r) => {
                const Icon = r.icon
                const active = activePanel === r.id
                return (
                  <button
                    key={r.id}
                    onClick={() => setPanel(r.id)}
                    className={clsx(
                      'flex items-center gap-3 w-full px-3 py-2 text-left transition-colors',
                      active
                        ? 'text-cyan bg-cyan-glow border-r-2 border-cyan'
                        : 'text-text-secondary hover:text-text-primary hover:bg-surface-raised',
                    )}
                  >
                    <Icon size={14} className={active ? 'text-cyan' : ''} />
                    <span className="text-[10px] font-mono uppercase leading-none truncate">{r.label}</span>
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
