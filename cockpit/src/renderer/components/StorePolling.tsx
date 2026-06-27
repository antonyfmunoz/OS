import { useExecutionSummaryStore } from '../stores/executionSummaryStore'
import { useUnifiedWorkstationStore } from '../stores/unifiedWorkstationStore'
import { useUnifiedApprovalStore } from '../stores/unifiedApprovalStore'
import { useEngineeringStore } from '../stores/engineeringStore'
import { usePolling } from '../hooks/usePolling'

export function StorePolling() {
  const fetchExecution = useExecutionSummaryStore((s) => s.fetchSummary)
  const fetchWorkstation = useUnifiedWorkstationStore((s) => s.fetchSnapshot)
  const fetchPending = useUnifiedApprovalStore((s) => s.fetchPending)
  const fetchByUrgency = useUnifiedApprovalStore((s) => s.fetchByUrgency)
  const fetchPlans = useEngineeringStore((s) => s.fetchPlans)

  usePolling(fetchExecution, 5000, true, 0)
  usePolling(fetchWorkstation, 5000, true, 200)
  usePolling(fetchPending, 5000, true, 400)
  usePolling(fetchByUrgency, 5000, true, 600)
  usePolling(fetchPlans, 5000, true, 800)

  return null
}
