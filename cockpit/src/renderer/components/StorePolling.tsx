import { useExecutionSummaryStore } from '../stores/executionSummaryStore'
import { usePolling } from '../hooks/usePolling'

export function StorePolling() {
  const fetchExecution = useExecutionSummaryStore((s) => s.fetchSummary)

  usePolling(fetchExecution, 5000, true, 0)

  return null
}
