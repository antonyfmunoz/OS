import { useEffect } from 'react'
import { LeftRail } from './components/LeftRail.tsx'
import { StatusBar } from './components/StatusBar.tsx'
import { PresenceLayer } from './components/PresenceOverlay.tsx'
import { VoiceOrb } from './components/VoiceOrb.tsx'
import { CameraFeed } from './components/CameraFeed.tsx'
import { useCockpitStore } from './stores/cockpitStore.ts'
import { connectWebSocket, disconnectWebSocket } from './lib/ws-client.ts'

import { CommandCenter } from './views/CommandCenter.tsx'
import { Agents } from './views/Agents.tsx'
import { Tasks } from './views/Tasks.tsx'
import { Activity } from './views/Activity.tsx'
import { Comms } from './views/Comms.tsx'
import { Approvals } from './views/Approvals.tsx'
import { Workflows } from './views/Workflows.tsx'
import { Awareness } from './views/Awareness.tsx'
import { Tracking } from './views/Tracking.tsx'
import { Production } from './views/Production.tsx'
import { Context } from './views/Context.tsx'
import { Knowledge } from './views/Knowledge.tsx'
import { Analytics } from './views/Analytics.tsx'
import { Experiments } from './views/Experiments.tsx'
import { Skills } from './views/Skills.tsx'
import { Infrastructure } from './views/Infrastructure.tsx'
import { Profile } from './views/Profile.tsx'
import { Settings } from './views/Settings.tsx'
import type { RouteId } from './types/routes.ts'
import type { ReactNode } from 'react'

const VIEW_MAP: Record<RouteId, () => ReactNode> = {
  'command-center': CommandCenter,
  agents: Agents,
  tasks: Tasks,
  activity: Activity,
  comms: Comms,
  approvals: Approvals,
  workflows: Workflows,
  awareness: Awareness,
  tracking: Tracking,
  production: Production,
  context: Context,
  knowledge: Knowledge,
  analytics: Analytics,
  experiments: Experiments,
  skills: Skills,
  infrastructure: Infrastructure,
  profile: Profile,
  settings: Settings,
}

export function App() {
  const { route } = useCockpitStore()
  const View = VIEW_MAP[route]

  useEffect(() => {
    connectWebSocket()
    useCockpitStore.getState().fetchAll()
    return () => disconnectWebSocket()
  }, [])

  return (
    <div className="flex h-screen bg-canvas overflow-hidden">
      <LeftRail />
      <div className="flex-1 flex flex-col min-w-0">
        <main className="flex-1 overflow-hidden">
          <View />
        </main>
        <StatusBar />
      </div>
      <PresenceLayer />
      <CameraFeed />
      <VoiceOrb />
    </div>
  )
}
