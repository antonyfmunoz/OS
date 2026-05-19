import { BarChart3 } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Analytics() {
  return (
    <ViewStub
      title="Analytics"
      icon={BarChart3}
      description="Substrate performance. Metrics, costs, throughput, and health trends across all infrastructure and agents."
      features={[
        'Model usage and cost breakdown',
        'Agent performance metrics',
        'Ingestion throughput charts',
        'Error rate trends',
        'Resource utilization history',
      ]}
    />
  )
}
