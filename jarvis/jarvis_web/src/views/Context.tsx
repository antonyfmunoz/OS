import { Layers } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Context() {
  return (
    <ViewStub
      title="Context"
      icon={Layers}
      description="World model browser. Navigate the substrate's understanding of reality — ontology, observations, relationships."
      features={[
        'Ontology browser (primitives, constructs)',
        'Observation explorer with evidence',
        'Relationship graph visualization',
        'Domain projection viewer',
        'Context search across all layers',
      ]}
    />
  )
}
