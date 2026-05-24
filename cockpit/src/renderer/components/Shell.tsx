import { TitleBar } from './TitleBar'
import { NavRail } from './NavRail'
import { HudBar } from './HudBar'
import { ChatDrawer } from './ChatDrawer'
import { useCockpitStore } from '../stores/cockpitStore'
import { DashboardPanel } from '../panels/DashboardPanel'

function PanelPlaceholder({ name }: { name: string }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <p className="font-mono text-lg mb-1" style={{ color: 'var(--accent-cyan)' }}>
          {name}
        </p>
        <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
          panel coming next phase
        </p>
      </div>
    </div>
  )
}

function ActivePanel() {
  const activePanel = useCockpitStore((s) => s.activePanel)

  switch (activePanel) {
    case 'dashboard':
      return <DashboardPanel />
    case 'agents':
      return <PanelPlaceholder name="Fleet Command" />
    case 'tasks':
      return <PanelPlaceholder name="Operations Board" />
    case 'approvals':
      return <PanelPlaceholder name="Governance Gate" />
    case 'knowledge':
      return <PanelPlaceholder name="World Model Explorer" />
    case 'analytics':
      return <PanelPlaceholder name="Intelligence Metrics" />
    case 'editor':
      return <PanelPlaceholder name="IDE" />
    case 'settings':
      return <PanelPlaceholder name="System Configuration" />
    case 'activity':
      return <PanelPlaceholder name="Event Intelligence" />
    default:
      return <DashboardPanel />
  }
}

export function Shell() {
  return (
    <div className="flex flex-col h-screen" style={{ background: 'var(--bg)' }}>
      <TitleBar />

      <div className="flex flex-1 overflow-hidden">
        <NavRail />

        {/* Main workspace */}
        <main
          className="flex-1 overflow-hidden"
          style={{ background: 'var(--surface-1)' }}
        >
          <ActivePanel />
        </main>

        <ChatDrawer />
      </div>

      <HudBar />
    </div>
  )
}
