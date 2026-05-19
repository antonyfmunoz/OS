import { Settings as SettingsIcon } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Settings() {
  return (
    <ViewStub
      title="Settings"
      icon={SettingsIcon}
      description="Configuration. Model routing, governance policies, notification rules, and substrate parameters."
      features={[
        'Model routing configuration',
        'Governance policy editor',
        'Notification rules',
        'API key management',
        'System parameters and tuning',
      ]}
    />
  )
}
