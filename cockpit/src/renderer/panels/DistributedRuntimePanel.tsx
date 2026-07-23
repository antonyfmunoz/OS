// Distributed Runtime panel — RETIRED (MVP Wave 2 convergence). Its worker /
// device / capacity views converged into the one canonical Execution surface
// (Workers + Environments). Non-executable redirect stub kept so imports don't
// dead-link; the export name is unchanged.
import { useEffect } from 'react'
import { useCockpitStore, type Panel } from '../stores/cockpitStore'
import { resolvePanelId } from './registry'

export function DistributedRuntimePanel() {
  useEffect(() => {
    useCockpitStore.getState().setPanel(resolvePanelId('distributedruntime') as Panel)
  }, [])
  return (
    <div className="flex items-center justify-center h-full text-[11px] font-mono text-text-tertiary">
      This surface has converged into Execution.
    </div>
  )
}
