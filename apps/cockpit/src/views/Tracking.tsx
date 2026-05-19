import { Crosshair } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Tracking() {
  return (
    <ViewStub
      title="Tracking"
      icon={Crosshair}
      description="Entities and how they change. Track any entity across time — people, companies, projects, metrics."
      features={[
        'Entity registry with change history',
        'Relationship graph between entities',
        'Change detection and alerts',
        'Custom entity type definitions',
        'Timeline view per entity',
      ]}
    />
  )
}
