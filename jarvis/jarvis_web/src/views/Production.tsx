import { Factory } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Production() {
  return (
    <ViewStub
      title="Production"
      icon={Factory}
      description="Manufacturing and fulfillment when configured. Content pipelines, product delivery, and output tracking."
      features={[
        'Content production pipeline',
        'Output queue and status',
        'Quality gates and review',
        'Delivery tracking per channel',
        'Production rate metrics',
      ]}
    />
  )
}
