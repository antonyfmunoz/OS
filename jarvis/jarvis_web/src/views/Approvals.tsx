import { ShieldCheck } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Approvals() {
  return (
    <ViewStub
      title="Approvals"
      icon={ShieldCheck}
      description="Decisions requiring authority. Governance queue with risk assessment, approval workflows, and audit trail."
      features={[
        'Pending approval queue with risk badges',
        'Approve/deny with rationale capture',
        'Auto-approval policy configuration',
        'Audit trail for all decisions',
        'Delegation and escalation rules',
      ]}
    />
  )
}
