import { useEffect } from 'react'
import { useCockpitStore } from '../stores/cockpitStore'
import { VoiceWaveform } from './VoiceWaveform'
import { useVoiceStore } from '../stores/voiceStore'
import { startVoice } from '../api/voice-controller'

export function FabSmall() {
  const cycleWindowMode = useCockpitStore((s) => s.cycleWindowMode)
  const micState = useVoiceStore((s) => s.micState)

  useEffect(() => {
    if (micState === 'idle') startVoice()
  }, [micState])

  return (
    <button
      onClick={() => cycleWindowMode('expand')}
      className="flex items-center justify-center rounded-full select-none"
      style={{
        width: 48,
        height: 48,
        background: 'var(--bg)',
        border: '1px solid var(--border)',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.4)',
      }}
      title="Expand"
    >
      <VoiceWaveform />
    </button>
  )
}
