import { useEffect } from 'react'
import { StorePolling } from './StorePolling'
import { TitleBar } from './TitleBar'
import { ControlPanel } from './ControlPanel'
import { HudBar } from './HudBar'
import { CommandPalette } from './CommandPalette'
import { FabLarge } from './FabLarge'
import { FabMedium } from './FabMedium'
import { FabSmall } from './FabSmall'
import { RightDrawer } from './RightDrawer'
import { useCockpitStore } from '../stores/cockpitStore'
import { useVoiceDetection } from '../hooks/useVoiceDetection'
import { useDeviceSessionStore } from '../stores/deviceSessionStore'
import { UnifiedCanvasWorkspace } from './canvas/UnifiedCanvasWorkspace'
import { ErrorBoundary } from './ErrorBoundary'
import { CallOverlay } from './CallOverlay'
import { ResumeCard } from './ResumeCard'
import { VoiceCommandBar } from './VoiceCommandBar'

export function Shell() {
  const windowMode = useCockpitStore((s) => s.windowMode)
  const initializeDeviceSession = useDeviceSessionStore((s) => s.initialize)
  const teardownDeviceSession = useDeviceSessionStore((s) => s.teardown)
  useVoiceDetection()

  useEffect(() => {
    initializeDeviceSession()
    return () => teardownDeviceSession()
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  if (windowMode === 'invisible') return null

  if (windowMode === 'small-fab') {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: 'transparent' }}>
        <FabSmall />
      </div>
    )
  }

  if (windowMode === 'medium-fab') {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: 'transparent' }}>
        <FabMedium />
      </div>
    )
  }

  if (windowMode === 'large-fab') {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: 'transparent' }}>
        <FabLarge />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-surface">
      <StorePolling />
      <TitleBar />

      <main className="flex-1 overflow-hidden bg-surface relative" style={{ paddingBottom: "var(--spacing-hud-height)" }}>
        <ErrorBoundary>
          <UnifiedCanvasWorkspace />
        </ErrorBoundary>
        <ControlPanel />
        <RightDrawer />
        <CallOverlay />
        <ResumeCard />
      </main>

      <HudBar />
      {Boolean((window as Record<string, unknown>).cockpit) && <VoiceCommandBar />}
      <CommandPalette />
    </div>
  )
}
