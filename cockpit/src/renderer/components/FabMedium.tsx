import { useCockpitStore } from '../stores/cockpitStore'
import { VoiceWaveform } from './VoiceWaveform'
import { useVoiceStore } from '../stores/voiceStore'

const MODE_COLORS: Record<string, string> = {
  EXECUTE: 'var(--accent-green)',
  PLAN: 'var(--accent-amber)',
  REVIEW: 'var(--accent-purple)',
}

export function FabMedium() {
  const mode = useCockpitStore((s) => s.mode)
  const cycleWindowMode = useCockpitStore((s) => s.cycleWindowMode)
  const micState = useVoiceStore((s) => s.micState)

  return (
    <div
      className="flex items-center gap-2 px-3 py-2 rounded-full select-none"
      style={{
        background: 'var(--bg)',
        border: '1px solid var(--border)',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.4)',
      }}
    >
      <span
        className="w-2 h-2 rounded-full flex-shrink-0"
        style={{ background: MODE_COLORS[mode] }}
      />

      <button
        onClick={() => {
          if (micState === 'idle') window.cockpit?.voice.start()
          else window.cockpit?.voice.stop()
        }}
        className="flex items-center justify-center w-6 h-6 rounded"
        style={{
          color: micState !== 'idle' ? 'var(--accent-cyan)' : 'var(--text-tertiary)',
        }}
      >
        {micState !== 'idle' ? <VoiceWaveform /> : <span className="text-xs">🎤</span>}
      </button>

      <button
        onClick={() => cycleWindowMode('expand')}
        className="text-xs"
        style={{ color: 'var(--text-tertiary)' }}
        title="Expand"
      >
        ↑
      </button>
      <button
        onClick={() => cycleWindowMode('shrink')}
        className="text-xs"
        style={{ color: 'var(--text-tertiary)' }}
        title="Shrink"
      >
        ↓
      </button>
    </div>
  )
}
