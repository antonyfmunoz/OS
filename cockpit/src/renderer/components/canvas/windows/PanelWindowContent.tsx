import { lazy, Suspense } from 'react'
import { resolvePanelId } from '../../../panels/registry'

const PANEL_COMPONENTS: Record<string, React.LazyExoticComponent<React.ComponentType>> = {
  dashboard: lazy(() => import('../../../panels/DashboardPanel').then(m => ({ default: m.DashboardPanel }))),
  commandcenter: lazy(() => import('../../../panels/CommandCenterPanel').then(m => ({ default: m.CommandCenterPanel }))),
  work: lazy(() => import('../../../panels/WorkPanel').then(m => ({ default: m.WorkPanel }))),
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
  tasks: lazy(() => import('../../../panels/TasksPanel').then(m => ({ default: m.TasksPanel }))),
  strategy: lazy(() => import('../../../panels/StrategyPanel').then(m => ({ default: m.StrategyPanel }))),
  tickloop: lazy(() => import('../../../panels/TickLoopPanel').then(m => ({ default: m.TickLoopPanel }))),
  projections: lazy(() => import('../../../panels/ProjectionPanel').then(m => ({ default: m.ProjectionPanel }))),
  continuity: lazy(() => import('../../../panels/ContinuityPanel').then(m => ({ default: m.ContinuityPanel }))),
  presence: lazy(() => import('../../../panels/PresencePanel').then(m => ({ default: m.PresencePanel }))),
  commands: lazy(() => import('../../../panels/CommandsPanel').then(m => ({ default: m.CommandsPanel }))),
  workstation: lazy(() => import('../../../panels/WorkstationPanel').then(m => ({ default: m.WorkstationPanel }))),
  sessions: lazy(() => import('../../../panels/SessionPanel').then(m => ({ default: m.SessionPanel }))),
  execcoord: lazy(() => import('../../../panels/ExecCoordPanel').then(m => ({ default: m.ExecCoordPanel }))),
  executor: lazy(() => import('../../../panels/ExecutorPanel').then(m => ({ default: m.ExecutorPanel }))),
  organismloop: lazy(() => import('../../../panels/OrganismLoopPanel').then(m => ({ default: m.OrganismLoopPanel }))),
  operatortimeline: lazy(() => import('../../../panels/OperatorTimelinePanel').then(m => ({ default: m.OperatorTimelinePanel }))),
  realitytimeline: lazy(() => import('../../../panels/RealityTimelinePanel').then(m => ({ default: m.RealityTimelinePanel }))),
  realityintelligence: lazy(() => import('../../../panels/RealityIntelligencePanel').then(m => ({ default: m.RealityIntelligencePanel }))),
  engineering: lazy(() => import('../../../panels/EngineeringPanel').then(m => ({ default: m.EngineeringPanel }))),
  intent: lazy(() => import('../../../panels/IntentPanel').then(m => ({ default: m.IntentPanel }))),
  capabilitymap: lazy(() => import('../../../panels/CapabilityMapPanel').then(m => ({ default: m.CapabilityMapPanel }))),
  mvpreadiness: lazy(() => import('../../../panels/MVPReadinessPanel').then(m => ({ default: m.MVPReadinessPanel }))),
  strategic: lazy(() => import('../../../panels/StrategicPanel').then(m => ({ default: m.StrategicPanel }))),
  memory: lazy(() => import('../../../panels/MemoryPanel').then(m => ({ default: m.MemoryPanel }))),
  capabilities: lazy(() => import('../../../panels/CapabilitiesPanel').then(m => ({ default: m.CapabilitiesPanel }))),
  workintelligence: lazy(() => import('../../../panels/WorkIntelligencePanel').then(m => ({ default: m.WorkIntelligencePanel }))),
  learning: lazy(() => import('../../../panels/LearningPanel').then(m => ({ default: m.LearningPanel }))),
  prediction: lazy(() => import('../../../panels/PredictionPanel').then(m => ({ default: m.PredictionPanel }))),
  executive: lazy(() => import('../../../panels/ExecutivePanel').then(m => ({ default: m.ExecutivePanel }))),
  actions: lazy(() => import('../../../panels/ActionsPanel').then(m => ({ default: m.ActionsPanel }))),
  distributedruntime: lazy(() => import('../../../panels/DistributedRuntimePanel').then(m => ({ default: m.DistributedRuntimePanel }))),
  operatorcontinuity: lazy(() => import('../../../panels/OperatorContinuityPanel')),
  operatorhome: lazy(() => import('../../../panels/OperatorHomePanel')),
  screenawareness: lazy(() => import('../../../panels/ScreenAwarenessPanel')),
  servicegraph: lazy(() => import('../../../panels/ServiceGraphPanel')),
  stateauthority: lazy(() => import('../../../panels/StateAuthorityPanel')),
  umhnode: lazy(() => import('../../../panels/UMHNodePanel')),
  workspacetopology: lazy(() => import('../../../panels/WorkspaceTopologyPanel')),
  proofinspector: lazy(() => import('../../../panels/ProofInspectorPanel').then(m => ({ default: m.ProofInspectorPanel }))),
  recoverydashboard: lazy(() => import('../../../panels/RecoveryDashboardPanel').then(m => ({ default: m.RecoveryDashboardPanel }))),
  realitygraph: lazy(() => import('../../../panels/RealityGraphPanel').then(m => ({ default: m.RealityGraphPanel }))),
  projectionmirrors: lazy(() => import('../../../panels/ProjectionMirrorsPanel').then(m => ({ default: m.ProjectionMirrorsPanel }))),
  intentloop: lazy(() => import('../../../panels/IntentLoopPanel').then(m => ({ default: m.IntentLoopPanel }))),
  workdetail: lazy(() => import('../../../panels/WorkDetailPanel').then(m => ({ default: m.WorkDetailPanel }))),
  objectiveplan: lazy(() => import('../../../panels/WorkDetailPanel').then(m => ({ default: m.WorkDetailPanel }))),
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

  // Retired/alias ids resolve to their canonical component (never a stub).
  const Component = PANEL_COMPONENTS[resolvePanelId(panelId)] ?? PANEL_COMPONENTS[panelId]
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
