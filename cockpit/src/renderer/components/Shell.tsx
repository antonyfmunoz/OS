import { TitleBar } from './TitleBar'
import { LeftRail } from './LeftRail'
import { HudBar } from './HudBar'
import { ControlPanel } from './ControlPanel'
import { RightRail } from './RightRail'
import { CommandPalette } from './CommandPalette'
import { FabLarge } from './FabLarge'
import { FabMedium } from './FabMedium'
import { FabSmall } from './FabSmall'
import { useCockpitStore } from '../stores/cockpitStore'
import { useVoiceDetection } from '../hooks/useVoiceDetection'
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
import { CommsPanel } from '../panels/CommsPanel'
import { WorkflowsPanel } from '../panels/WorkflowsPanel'
import { TrackingPanel } from '../panels/TrackingPanel'
import { SkillsPanel } from '../panels/SkillsPanel'
import { ExperimentsPanel } from '../panels/ExperimentsPanel'
import { InfrastructurePanel } from '../panels/InfrastructurePanel'
import { ProfilePanel } from '../panels/ProfilePanel'
import { OrganismPanel } from '../panels/OrganismPanel'
import { IntelligencePanel } from '../panels/IntelligencePanel'

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
    case 'comms':
      return <CommsPanel />
    case 'workflows':
      return <WorkflowsPanel />
    case 'tracking':
      return <TrackingPanel />
    case 'skills':
      return <SkillsPanel />
    case 'experiments':
      return <ExperimentsPanel />
    case 'infrastructure':
      return <InfrastructurePanel />
    case 'profile':
      return <ProfilePanel />
    case 'organism':
      return <OrganismPanel />
    case 'intelligence':
      return <IntelligencePanel />
    default:
      return <DashboardPanel />
  }
}

export function Shell() {
  const windowMode = useCockpitStore((s) => s.windowMode)
  useVoiceDetection()

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
    <div className="flex flex-col h-screen bg-canvas">
      <TitleBar />

      <div className="flex flex-1 overflow-hidden">
        <LeftRail />

        <div className="flex-1 flex flex-col overflow-hidden">
          <ControlPanel />
          <main className="flex-1 overflow-hidden bg-surface">
            <ActivePanel />
          </main>
        </div>

        <RightRail />
      </div>

      <HudBar />
      <CommandPalette />
    </div>
  )
}
