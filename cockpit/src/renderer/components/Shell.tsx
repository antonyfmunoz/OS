import { TitleBar } from './TitleBar'
import { NavRail } from './NavRail'
import { HudBar } from './HudBar'
import { ChatDrawer } from './ChatDrawer'
import { CommandPalette } from './CommandPalette'
import { useCockpitStore } from '../stores/cockpitStore'
import { DashboardPanel } from '../panels/DashboardPanel'
import { AgentsPanel } from '../panels/AgentsPanel'
import { TasksPanel } from '../panels/TasksPanel'
import { ApprovalsPanel } from '../panels/ApprovalsPanel'
import { ActivityPanel } from '../panels/ActivityPanel'
import { KnowledgePanel } from '../panels/KnowledgePanel'
import { AnalyticsPanel } from '../panels/AnalyticsPanel'
import { SettingsPanel } from '../panels/SettingsPanel'
import { EditorPanel } from '../panels/EditorPanel'

function ActivePanel() {
  const activePanel = useCockpitStore((s) => s.activePanel)

  switch (activePanel) {
    case 'dashboard':
      return <DashboardPanel />
    case 'agents':
      return <AgentsPanel />
    case 'tasks':
      return <TasksPanel />
    case 'approvals':
      return <ApprovalsPanel />
    case 'activity':
      return <ActivityPanel />
    case 'knowledge':
      return <KnowledgePanel />
    case 'analytics':
      return <AnalyticsPanel />
    case 'editor':
      return <EditorPanel />
    case 'settings':
      return <SettingsPanel />
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

        <main
          className="flex-1 overflow-hidden"
          style={{ background: 'var(--surface-1)' }}
        >
          <ActivePanel />
        </main>

        <ChatDrawer />
      </div>

      <HudBar />
      <CommandPalette />
    </div>
  )
}
