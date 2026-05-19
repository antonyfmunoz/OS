import { User } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Profile() {
  return (
    <ViewStub
      title="Profile"
      icon={User}
      description="Light optional domain panels. Personal context, preferences, and domain-specific configuration when needed."
      features={[
        'User identity and preferences',
        'Domain panel configuration',
        'Notification preferences',
        'Session history',
        'Access and permissions',
      ]}
    />
  )
}
