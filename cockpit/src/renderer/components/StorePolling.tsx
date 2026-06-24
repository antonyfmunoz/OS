import { useExecutionSummaryStore } from '../stores/executionSummaryStore'
import { useUnifiedWorkstationStore } from '../stores/unifiedWorkstationStore'
import { usePolling } from '../hooks/usePolling'

export function StorePolling() {
  const fetchExecution = useExecutionSummaryStore((s) => s.fetchSummary)
  const fetchWorkstation = useUnifiedWorkstationStore((s) => s.fetchSnapshot)

  usePolling(fetchExecution, 5000, true, 0)
  usePolling(fetchWorkstation, 5000, true, 200)

  return null
}
