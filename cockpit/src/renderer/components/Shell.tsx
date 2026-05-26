import { TitleBar } from './TitleBar'
import { NavRail } from './NavRail'
import { HudBar } from './HudBar'
import { ChatDrawer } from './ChatDrawer'
import { CommandPalette } from './CommandPalette'
import { FabLarge } from './FabLarge'
import { FabMedium } from './FabMedium'
import { FabSmall } from './FabSmall'
import { VoiceCommandBar } from './VoiceCommandBar'
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
import { ExecutionPanel } from '../panels/ExecutionPanel'
import { PortfolioPanel } from '../panels/PortfolioPanel'
import { CompanyPanel } from '../panels/CompanyPanel'

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
    case 'execution':
      return <ExecutionPanel />
    case 'portfolio':
      return <PortfolioPanel />
    case 'company':
      return <CompanyPanel />
    default:
      return <DashboardPanel />
  }
}

export function Shell() {
  const windowMode = useCockpitStore((s) => s.windowMode)

  if (windowMode === 'invisible') return null

  if (windowMode === 'small-fab') {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: 'transparent' }}>
        <FabSmall />
      </div>
    )
  }

  if (windowMode === 'medium-fab') {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: 'transparent' }}>
        <FabMedium />
      </div>
    )
  }

  if (windowMode === 'large-fab') {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: 'transparent' }}>
        <FabLarge />
      </div>
    )
  }

  return (
    <div className="relative flex flex-col h-screen" style={{ background: 'var(--bg)' }}>
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

      <VoiceCommandBar />
      <HudBar />
      <CommandPalette />
    </div>
  )
}
