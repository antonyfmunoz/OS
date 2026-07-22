// Tasks panel — RETIRED (MVP Wave 1 convergence). The Task surface converged
// into the canonical Work kanban. This module is a non-executable redirect stub
// kept so imports don't dead-link; the export name is unchanged.
import { useEffect } from 'react'
import { useCockpitStore, type Panel } from '../stores/cockpitStore'
import { resolvePanelId } from './registry'

export function TasksPanel() {
  useEffect(() => {
    useCockpitStore.getState().setPanel(resolvePanelId('tasks') as Panel)
  }, [])
  return (
    <div className="flex items-center justify-center h-full text-[11px] font-mono text-text-tertiary">
      This surface has converged into Work.
    </div>
  )
}
