import { ListChecks } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Tasks() {
  return (
    <ViewStub
      title="Tasks"
      icon={ListChecks}
      description="Work in motion across all dimensions. Track work packets, assignments, progress, and dependencies."
      features={[
        'Work packet board (kanban/list/timeline)',
        'Agent assignment and delegation',
        'Dependency graph visualization',
        'Priority and risk indicators',
        'Batch operations and filters',
      ]}
    />
  )
}
