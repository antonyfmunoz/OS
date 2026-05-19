import { MessageSquare } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Comms() {
  return (
    <ViewStub
      title="Comms"
      icon={MessageSquare}
      description="Conversations between agents, user, and people. Unified communication surface across all channels."
      features={[
        'Agent-to-agent message log',
        'Human-agent conversation threads',
        'Channel integration (Discord, email)',
        'Message search and threading',
        'Communication protocol enforcement',
      ]}
    />
  )
}
