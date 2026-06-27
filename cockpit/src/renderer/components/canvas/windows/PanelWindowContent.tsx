import { lazy, Suspense } from 'react'

const PANEL_COMPONENTS: Record<string, React.LazyExoticComponent<React.ComponentType>> = {
  dashboard: lazy(() => import('../../../panels/DashboardPanel').then(m => ({ default: m.DashboardPanel }))),
  commandcenter: lazy(() => import('../../../panels/CommandCenterPanel').then(m => ({ default: m.CommandCenterPanel }))),
  work: lazy(() => import('../../../panels/WorkPanel').then(m => ({ default: m.WorkPanel }))),
  agents: lazy(() => import('../../../panels/AgentsPanel').then(m => ({ default: m.AgentsPanel }))),
  approvals: lazy(() => import('../../../panels/ApprovalsPanel').then(m => ({ default: m.ApprovalsPanel }))),
  activity: lazy(() => import('../../../panels/ActivityPanel').then(m => ({ default: m.ActivityPanel }))),
  knowledge: lazy(() => import('../../../panels/KnowledgePanel').then(m => ({ default: m.KnowledgePanel }))),
  analytics: lazy(() => import('../../../panels/AnalyticsPanel').then(m => ({ default: m.AnalyticsPanel }))),
  editor: lazy(() => import('../../../panels/MetaIDEPanel').then(m => ({ default: m.MetaIDEPanel }))),
  execution: lazy(() => import('../../../panels/ExecutionPanel').then(m => ({ default: m.ExecutionPanel }))),
  organism: lazy(() => import('../../../panels/OrganismPanel').then(m => ({ default: m.OrganismPanel }))),
  organismmap: lazy(() => import('../../../panels/OrganismMapPanel').then(m => ({ default: m.OrganismMapPanel }))),
  settings: lazy(() => import('../../../panels/SettingsPanel').then(m => ({ default: m.SettingsPanel }))),
  goals: lazy(() => import('../../../panels/GoalPanel').then(m => ({ default: m.GoalPanel }))),
  operations: lazy(() => import('../../../panels/OperationsPanel').then(m => ({ default: m.OperationsPanel }))),
  governance: lazy(() => import('../../../panels/GovernancePanel').then(m => ({ default: m.GovernancePanel }))),
  browser: lazy(() => import('../../../panels/BrowserPanel').then(m => ({ default: m.BrowserPanel }))),
  vision: lazy(() => import('../../../panels/VisionPanel').then(m => ({ default: m.VisionPanel }))),
  broadcast: lazy(() => import('../../../panels/BroadcastPanel').then(m => ({ default: m.BroadcastPanel }))),
  rooms: lazy(() => import('../../../panels/ConferenceRoomsPanel').then(m => ({ default: m.ConferenceRoomsPanel }))),
  delegation: lazy(() => import('../../../panels/DelegationPanel').then(m => ({ default: m.DelegationPanel }))),
  unifiedexecution: lazy(() => import('../../../panels/UnifiedExecutionPanel').then(m => ({ default: m.UnifiedExecutionPanel }))),
  buildloop: lazy(() => import('../../../panels/BuildLoopPanel').then(m => ({ default: m.BuildLoopPanel }))),
  projectionintegration: lazy(() => import('../../../panels/ProjectionIntegrationPanel').then(m => ({ default: m.ProjectionIntegrationPanel }))),
  orchestratorawareness: lazy(() => import('../../../panels/OrchestratorPanel').then(m => ({ default: m.OrchestratorPanel }))),
  operatingloopview: lazy(() => import('../../../panels/OperatingLoopPanel').then(m => ({ default: m.OperatingLoopPanel }))),
  sessionresume: lazy(() => import('../../../panels/SessionResumePanel').then(m => ({ default: m.SessionResumePanel }))),
  tmux: lazy(() => import('../../../panels/TmuxPanel').then(m => ({ default: m.TmuxPanel }))),
  runtime: lazy(() => import('../../../panels/RuntimePanel').then(m => ({ default: m.RuntimePanel }))),
  portfolio: lazy(() => import('../../../panels/PortfolioPanel').then(m => ({ default: m.PortfolioPanel }))),
  company: lazy(() => import('../../../panels/CompanyPanel').then(m => ({ default: m.CompanyPanel }))),
  comms: lazy(() => import('../../../panels/CommsPanel').then(m => ({ default: m.CommsPanel }))),
  infrastructure: lazy(() => import('../../../panels/InfrastructurePanel').then(m => ({ default: m.InfrastructurePanel }))),
  profile: lazy(() => import('../../../panels/ProfilePanel').then(m => ({ default: m.ProfilePanel }))),
  intelligence: lazy(() => import('../../../panels/IntelligencePanel').then(m => ({ default: m.IntelligencePanel }))),
  worldmodel: lazy(() => import('../../../panels/WorldModelPanel').then(m => ({ default: m.WorldModelPanel }))),
  selfbuild: lazy(() => import('../../../panels/SelfBuildPanel').then(m => ({ default: m.SelfBuildPanel }))),
  universalwork: lazy(() => import('../../../panels/UniversalWorkPanel').then(m => ({ default: m.UniversalWorkPanel }))),
  propagation: lazy(() => import('../../../panels/PropagationGraphPanel')),
  operator: lazy(() => import('../../../panels/OperatorPanel').then(m => ({ default: m.OperatorPanel }))),
  skills: lazy(() => import('../../../panels/SkillsPanel').then(m => ({ default: m.SkillsPanel }))),
}

interface Props {
  panelId?: string
}

export function PanelWindowContent({ panelId }: Props) {
  if (!panelId) {
    return (
      <div className="flex items-center justify-center h-full" style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="text-[12px]">No panel selected</span>
      </div>
    )
  }

  const Component = PANEL_COMPONENTS[panelId]
  if (!Component) {
    return (
      <div className="flex items-center justify-center h-full" style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="text-[12px]">Panel: {panelId}</span>
      </div>
    )
  }

  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-full" style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="text-[12px]">Loading {panelId}...</span>
      </div>
    }>
      <div className="h-full overflow-auto">
        <Component />
      </div>
    </Suspense>
  )
}
