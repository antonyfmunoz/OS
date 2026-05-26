import { useVoiceStore } from '../stores/voiceStore'

export function VoiceWaveform() {
  const audioLevel = useVoiceStore((s) => s.audioLevel)
  const micState = useVoiceStore((s) => s.micState)

  if (micState === 'idle') return null

  const bars = 5
  const levels = Array.from({ length: bars }, (_, i) => {
    const offset = (i - Math.floor(bars / 2)) * 0.15
    const base = Math.max(0, Math.min(1, audioLevel + offset))
    return micState === 'listening' ? base : base * 0.3
  })

  return (
    <div className="flex items-end gap-px h-3">
      {levels.map((level, i) => (
        <div
          key={i}
          className="w-0.5 rounded-full transition-all duration-75"
          style={{
            height: `${Math.max(2, level * 12)}px`,
            background: micState === 'listening' ? 'var(--color-cyan)' : 'var(--color-warn)',
            opacity: 0.6 + level * 0.4,
          }}
        />
      ))}
    </div>
  )
}
