import { lazy, Suspense } from 'react'
import type { Panel } from '../../../stores/cockpitStore'

const PANEL_COMPONENTS: Record<string, React.LazyExoticComponent<React.ComponentType>> = {
  dashboard: lazy(() => import('../../../panels/DashboardPanel').then(m => ({ default: m.DashboardPanel }))),
  analytics: lazy(() => import('../../../panels/AnalyticsPanel').then(m => ({ default: m.AnalyticsPanel }))),
  knowledge: lazy(() => import('../../../panels/KnowledgePanel').then(m => ({ default: m.KnowledgePanel }))),
  activity: lazy(() => import('../../../panels/ActivityPanel').then(m => ({ default: m.ActivityPanel }))),
  execution: lazy(() => import('../../../panels/ExecutionPanel').then(m => ({ default: m.ExecutionPanel }))),
  organism: lazy(() => import('../../../panels/OrganismPanel').then(m => ({ default: m.OrganismPanel }))),
  settings: lazy(() => import('../../../panels/SettingsPanel').then(m => ({ default: m.SettingsPanel }))),
  approvals: lazy(() => import('../../../panels/ApprovalsPanel').then(m => ({ default: m.ApprovalsPanel }))),
  goals: lazy(() => import('../../../panels/GoalPanel').then(m => ({ default: m.GoalPanel }))),
  operations: lazy(() => import('../../../panels/OperationsPanel').then(m => ({ default: m.OperationsPanel }))),
  governance: lazy(() => import('../../../panels/GovernancePanel').then(m => ({ default: m.GovernancePanel }))),
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
