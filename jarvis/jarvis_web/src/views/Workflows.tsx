import { Workflow } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Workflows() {
  return (
    <ViewStub
      title="Workflows"
      icon={Workflow}
      description="Scheduled and composable patterns. Design, schedule, and monitor recurring operational workflows."
      features={[
        'Workflow designer (visual DAG)',
        'Schedule management (cron/event)',
        'Execution history and success rates',
        'Template library',
        'Workflow composition and nesting',
      ]}
    />
  )
}
