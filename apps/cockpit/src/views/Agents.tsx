import { Bot } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Agents() {
  return (
    <ViewStub
      title="Agents"
      icon={Bot}
      description="Intelligences working on your behalf. View active agents, their soul documents, capabilities, and current assignments."
      features={[
        'Agent roster with status indicators',
        'Soul document viewer',
        'Capability matrix',
        'Assignment history and performance',
        'Agent creation and configuration',
      ]}
    />
  )
}
