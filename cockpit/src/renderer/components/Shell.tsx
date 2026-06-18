import { useEffect } from 'react'
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
import { useDeviceSessionStore } from '../stores/deviceSessionStore'
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
import { WorldModelPanel } from '../panels/WorldModelPanel'
import { SelfBuildPanel } from '../panels/SelfBuildPanel'
import { UniversalWorkPanel } from '../panels/UniversalWorkPanel'
import PropagationGraphPanel from '../panels/PropagationGraphPanel'
import { OperatorPanel } from '../panels/OperatorPanel'
import { RuntimePanel } from '../panels/RuntimePanel'
import { TmuxPanel } from '../panels/TmuxPanel'
import { WorkspacePanel } from '../panels/WorkspacePanel'
import { WorkPanel } from '../panels/WorkPanel'
import { CommandCenterPanel } from '../panels/CommandCenterPanel'
import { VisionPanel } from '../panels/VisionPanel'
import { BroadcastPanel } from '../panels/BroadcastPanel'
import { ConferenceRoomsPanel } from '../panels/ConferenceRoomsPanel'
import { StrategyPanel } from '../panels/StrategyPanel'
import { TickLoopPanel } from '../panels/TickLoopPanel'
import { ProjectionPanel } from '../panels/ProjectionPanel'
import { ContinuityPanel } from '../panels/ContinuityPanel'
import { PresencePanel } from '../panels/PresencePanel'
import { CommandsPanel } from '../panels/CommandsPanel'
import { WorkstationPanel } from '../panels/WorkstationPanel'
import { SessionPanel } from '../panels/SessionPanel'
import { ExecCoordPanel } from '../panels/ExecCoordPanel'
import { ExecutorPanel } from '../panels/ExecutorPanel'
import { OrganismLoopPanel } from '../panels/OrganismLoopPanel'
import { OperatorTimelinePanel } from '../panels/OperatorTimelinePanel'
import { RealityTimelinePanel } from '../panels/RealityTimelinePanel'
import { RealityIntelligencePanel } from '../panels/RealityIntelligencePanel'
import { MetaIDEPanel } from '../panels/MetaIDEPanel'
import { EngineeringPanel } from '../panels/EngineeringPanel'
import { OrganismMapPanel } from '../panels/OrganismMapPanel'
import { IntentPanel } from '../panels/IntentPanel'
import { CapabilityMapPanel } from '../panels/CapabilityMapPanel'
import { UnifiedExecutionPanel } from '../panels/UnifiedExecutionPanel'
import { BuildLoopPanel } from '../panels/BuildLoopPanel'
import { ProjectionIntegrationPanel } from '../panels/ProjectionIntegrationPanel'
import { OrchestratorPanel } from '../panels/OrchestratorPanel'
import { OperatingLoopPanel } from '../panels/OperatingLoopPanel'
import { SessionResumePanel } from '../panels/SessionResumePanel'
import { MVPReadinessPanel } from '../panels/MVPReadinessPanel'
import { DelegationPanel } from '../panels/DelegationPanel'
import { RealityGraphPanel } from '../panels/RealityGraphPanel'
import { StrategicPanel } from '../panels/StrategicPanel'
import { GoalPanel } from '../panels/GoalPanel'
import { MemoryPanel } from '../panels/MemoryPanel'
import { CapabilitiesPanel } from '../panels/CapabilitiesPanel'
import { WorkIntelligencePanel } from '../panels/WorkIntelligencePanel'
import { LearningPanel } from '../panels/LearningPanel'
import { PredictionPanel } from '../panels/PredictionPanel'
import { ErrorBoundary } from './ErrorBoundary'
import { CallOverlay } from './CallOverlay'

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
    case 'worldmodel':
      return <WorldModelPanel />
    case 'selfbuild':
      return <SelfBuildPanel />
    case 'universalwork':
      return <UniversalWorkPanel />
    case 'propagation':
      return <PropagationGraphPanel />
    case 'operator':
      return <OperatorPanel />
    case 'runtime':
      return <RuntimePanel />
    case 'tmux':
      return <TmuxPanel />
    case 'work':
      return <WorkPanel />
    case 'workspace':
      return <WorkspacePanel />
    case 'commandcenter':
      return <CommandCenterPanel />
    case 'vision':
      return <VisionPanel />
    case 'rooms':
      return <ErrorBoundary><ConferenceRoomsPanel /></ErrorBoundary>
    case 'broadcast':
      return <BroadcastPanel />
    case 'strategy':
      return <StrategyPanel />
    case 'tickloop':
      return <TickLoopPanel />
    case 'projections':
      return <ProjectionPanel />
    case 'continuity':
      return <ContinuityPanel />
    case 'presence':
      return <PresencePanel />
    case 'commands':
      return <CommandsPanel />
    case 'workstation':
      return <WorkstationPanel />
    case 'sessions':
      return <SessionPanel />
    case 'execcoord':
      return <ExecCoordPanel />
    case 'executor':
      return <ExecutorPanel />
    case 'organismloop':
      return <OrganismLoopPanel />
    case 'operatortimeline':
      return <OperatorTimelinePanel />
    case 'realitytimeline':
      return <RealityTimelinePanel />
    case 'realityintelligence':
      return <RealityIntelligencePanel />
    case 'metaide':
      return <MetaIDEPanel />
    case 'engineering':
      return <EngineeringPanel />
    case 'organismmap':
      return <OrganismMapPanel />
    case 'intent':
      return <IntentPanel />
    case 'capabilitymap':
      return <CapabilityMapPanel />
    case 'unifiedexecution':
      return <UnifiedExecutionPanel />
    case 'buildloop':
      return <BuildLoopPanel />
    case 'projectionintegration':
      return <ProjectionIntegrationPanel />
    case 'orchestratorawareness':
      return <OrchestratorPanel />
    case 'operatingloopview':
      return <OperatingLoopPanel />
    case 'sessionresume':
      return <SessionResumePanel />
    case 'mvpreadiness':
      return <MVPReadinessPanel />
    case 'delegation':
      return <DelegationPanel />
    case 'realitygraph':
      return <RealityGraphPanel />
    case 'strategic':
      return <StrategicPanel />
    case 'goals':
      return <GoalPanel />
    case 'memory':
      return <MemoryPanel />
    case 'capabilities':
      return <CapabilitiesPanel />
    case 'workintelligence':
      return <WorkIntelligencePanel />
    case 'learning':
      return <LearningPanel />
    case 'prediction':
      return <PredictionPanel />

    default:
      return <DashboardPanel />
  }
}

export function Shell() {
  const windowMode = useCockpitStore((s) => s.windowMode)
  const initializeDeviceSession = useDeviceSessionStore((s) => s.initialize)
  const teardownDeviceSession = useDeviceSessionStore((s) => s.teardown)
  useVoiceDetection()

  useEffect(() => {
    initializeDeviceSession()
    return () => teardownDeviceSession()
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

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
    <div className="flex flex-col h-screen bg-surface">
      <TitleBar />

      <div className="flex flex-1 overflow-hidden">
        <LeftRail />

        <div className="flex-1 flex flex-col overflow-hidden">
          <ControlPanel />
          <main className="flex-1 overflow-hidden bg-surface relative">
            <ActivePanel />
            <CallOverlay />
          </main>
        </div>

        <RightRail />
      </div>

      <HudBar />
      <CommandPalette />
    </div>
  )
}
