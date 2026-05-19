import { Activity as ActivityIcon } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Activity() {
  return (
    <ViewStub
      title="Activity"
      icon={ActivityIcon}
      description="Executions and traces happening now. Real-time stream of all substrate operations with filtering and drill-down."
      features={[
        'Real-time trace stream with WebSocket',
        'Filter by agent, status, risk level',
        'Trace detail drill-down',
        'Execution timeline visualization',
        'Error analysis and correlation',
      ]}
    />
  )
}
