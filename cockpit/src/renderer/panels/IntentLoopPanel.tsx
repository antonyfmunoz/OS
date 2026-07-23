// Intent Loop panel — RETIRED (MVP Wave 1 convergence). The intent loop
// converged into the Work Detail panel (Plan/Task detail). This module is a
// non-executable redirect stub kept so imports don't dead-link; the export name
// is unchanged.
import { useEffect } from 'react'
import { useCockpitStore, type Panel } from '../stores/cockpitStore'
import { resolvePanelId } from './registry'

export function IntentLoopPanel() {
  useEffect(() => {
    useCockpitStore.getState().setPanel(resolvePanelId('intentloop') as Panel)
  }, [])
  return (
    <div className="flex items-center justify-center h-full text-[11px] font-mono text-text-tertiary">
      This surface has converged into Plan Detail.
    </div>
  )
}
