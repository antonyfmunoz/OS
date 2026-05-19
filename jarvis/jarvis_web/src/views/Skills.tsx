import { Wrench } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Skills() {
  return (
    <ViewStub
      title="Skills"
      icon={Wrench}
      description="Capabilities and adapter registry. Browse, search, and manage the substrate's skill inventory."
      features={[
        'Skill catalog with search',
        'Adapter status and health',
        'Skill creation wizard',
        'Usage statistics per skill',
        'Dependency mapping',
      ]}
    />
  )
}
