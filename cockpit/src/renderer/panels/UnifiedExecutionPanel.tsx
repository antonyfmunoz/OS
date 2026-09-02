// Unified Execution panel — RETIRED (MVP Wave 2 convergence). Converged into the
// one canonical Execution surface. Non-executable redirect stub kept so imports
// don't dead-link; the export name is unchanged. Its former decision writes are
// gone — execution decisions are HUD-only.
import { useEffect } from 'react'
import { useCockpitStore, type Panel } from '../stores/cockpitStore'
import { resolvePanelId } from './registry'

export function UnifiedExecutionPanel() {
  useEffect(() => {
    useCockpitStore.getState().setPanel(resolvePanelId('unifiedexecution') as Panel)
  }, [])
  return (
    <div className="flex items-center justify-center h-full text-[11px] font-mono text-text-tertiary">
      This surface has converged into Execution.
    </div>
  )
}
