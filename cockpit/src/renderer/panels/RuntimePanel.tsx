// Runtime panel — RETIRED (MVP Wave 2 convergence). Converged into the one
// canonical Execution surface (Diagnostics). Non-executable redirect stub kept
// so imports don't dead-link; the export name is unchanged. Its former
// handoff-preview write is gone.
import { useEffect } from 'react'
import { useCockpitStore, type Panel } from '../stores/cockpitStore'
import { resolvePanelId } from './registry'

export function RuntimePanel() {
  useEffect(() => {
    useCockpitStore.getState().setPanel(resolvePanelId('runtime') as Panel)
  }, [])
  return (
    <div className="flex items-center justify-center h-full text-[11px] font-mono text-text-tertiary">
      This surface has converged into Execution.
    </div>
  )
}
