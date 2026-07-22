// Command Center panel — RETIRED (MVP Wave 1 convergence). Command entry
// converged into Cockpit Chat (the one conversational work seam). This module is
// a non-executable redirect stub kept so imports don't dead-link; the export
// name is unchanged. resolvePanelId('commands') → 'chat', which setPanel handles
// by opening the chat rail.
import { useEffect } from 'react'
import { useCockpitStore, type Panel } from '../stores/cockpitStore'
import { resolvePanelId } from './registry'

export function CommandsPanel() {
  useEffect(() => {
    useCockpitStore.getState().setPanel(resolvePanelId('commands') as Panel)
  }, [])
  return (
    <div className="flex items-center justify-center h-full text-[11px] font-mono text-text-tertiary">
      This surface has converged into Cockpit Chat.
    </div>
  )
}
