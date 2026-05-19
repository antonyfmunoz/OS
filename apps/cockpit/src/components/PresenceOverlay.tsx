import { useCockpitStore } from '../stores/cockpitStore.ts'

export function FloatingOverlay() {
  return (
    <div className="fixed bottom-4 right-4 w-80 h-48 wv-card p-3 bg-surface/95 backdrop-blur-sm border border-cyan-dim wv-glow-cyan z-50">
      <div className="wv-label mb-2">FLOATING OVERLAY — STUB</div>
      <div className="text-[10px] text-text-tertiary">
        Compact always-on-top view of critical metrics. Activates when cockpit is minimized.
      </div>
    </div>
  )
}

export function VoiceWaveAmbient() {
  return (
    <div className="fixed bottom-0 left-0 right-0 h-16 flex items-center justify-center z-50 pointer-events-none">
      <div className="flex items-end gap-0.5 h-8">
        {Array.from({ length: 32 }, (_, i) => (
          <div
            key={i}
            className="w-1 bg-cyan/30 rounded-full"
            style={{
              height: `${4 + Math.sin(i * 0.5) * 12 + Math.random() * 8}px`,
              animationDelay: `${i * 50}ms`,
            }}
          />
        ))}
      </div>
      <div className="absolute bottom-2 text-[9px] text-text-tertiary font-mono uppercase">
        Voice-Wave Ambient — Stub
      </div>
    </div>
  )
}

export function GhostBackground() {
  return (
    <div className="fixed inset-0 bg-canvas/95 z-40 flex items-center justify-center pointer-events-none">
      <div className="text-[11px] text-text-tertiary font-mono uppercase tracking-widest wv-pulse">
        Ghost Background — Processing
      </div>
    </div>
  )
}

export function PresenceLayer() {
  const { presenceMode } = useCockpitStore()

  switch (presenceMode) {
    case 'floating-overlay':
      return <FloatingOverlay />
    case 'voice-wave':
      return <VoiceWaveAmbient />
    case 'ghost-background':
      return <GhostBackground />
    case 'full-screen':
    default:
      return null
  }
}
