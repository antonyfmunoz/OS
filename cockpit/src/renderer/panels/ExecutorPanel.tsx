// Executor panel — RETIRED (MVP Wave 2 convergence). Converged into the one
// canonical Execution surface. Non-executable redirect stub kept so imports
// don't dead-link; the export name is unchanged. Its former free-text agent
// launcher and raw-fetch reads are gone — execution runs only under a governed,
// HUD-authorized attempt.
import { useEffect } from 'react'
import { useCockpitStore, type Panel } from '../stores/cockpitStore'
import { resolvePanelId } from './registry'

export function ExecutorPanel() {
  useEffect(() => {
    useCockpitStore.getState().setPanel(resolvePanelId('executor') as Panel)
  }, [])
  return (
    <div className="flex items-center justify-center h-full text-[11px] font-mono text-text-tertiary">
      This surface has converged into Execution.
    </div>
  )
}
