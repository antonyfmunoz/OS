import { FlaskConical } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Experiments() {
  return (
    <ViewStub
      title="Experiments"
      icon={FlaskConical}
      description="Sandbox, simulation, and self-modification proposals. Test changes before they affect reality."
      features={[
        'Experiment sandbox with isolation',
        'A/B test configuration and results',
        'Self-modification proposal review',
        'Simulation runner',
        'Experiment history and learnings',
      ]}
    />
  )
}
