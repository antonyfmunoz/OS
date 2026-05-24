import { useSystemStore } from '../stores/systemStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { useVoiceStore } from '../stores/voiceStore'

function StatusDot({ status }: { status: 'connected' | 'connecting' | 'disconnected' }) {
  const colors = {
    connected: 'var(--accent-green)',
    connecting: 'var(--accent-amber)',
    disconnected: 'var(--accent-red)',
  }
  return (
    <span
      className="inline-block w-[6px] h-[6px] rounded-full"
      style={{ background: colors[status] }}
    />
  )
}

function AudioMeter({ level }: { level: number }) {
  const bars = 5
  const active = Math.round(level * bars)
  return (
    <span className="inline-flex items-end gap-px h-3">
      {Array.from({ length: bars }, (_, i) => (
        <span
          key={i}
          className="w-[3px] rounded-sm transition-all duration-75"
          style={{
            height: `${((i + 1) / bars) * 100}%`,
            background: i < active ? 'var(--accent-cyan)' : 'var(--border-focus)',
          }}
        />
      ))}
    </span>
  )
}

export function HudBar() {
  const pulse = useSystemStore((s) => s.pulse)
  const meshNodes = useSystemStore((s) => s.meshNodes)
  const mode = useCockpitStore((s) => s.mode)
  const setMode = useCockpitStore((s) => s.setMode)
  const apiStatus = useCockpitStore((s) => s.apiStatus)
  const wsStatus = useCockpitStore((s) => s.wsStatus)
  const voiceStatus = useCockpitStore((s) => s.voiceStatus)
  const micState = useVoiceStore((s) => s.micState)
  const audioLevel = useVoiceStore((s) => s.audioLevel)

  const modes = ['EXECUTE', 'PLAN', 'REVIEW'] as const

  return (
    <footer
      className="flex items-center gap-4 px-3 select-none"
      style={{
        height: 'var(--hud-height)',
        background: 'var(--bg)',
        borderTop: '1px solid var(--border)',
      }}
    >
      {/* Agents */}
      <span className="hud-text flex items-center gap-1.5">
        <StatusDot status={pulse && pulse.active_agents > 0 ? 'connected' : 'disconnected'} />
        <span className="hud-value">{pulse?.active_agents ?? 0}</span> agents
      </span>

      {/* CPU */}
      <span className="hud-text">
        cpu <span className="hud-value">{pulse?.cpu_percent?.toFixed(0) ?? '—'}%</span>
      </span>

      {/* RAM */}
      <span className="hud-text">
        ram <span className="hud-value">{pulse?.memory_percent?.toFixed(0) ?? '—'}%</span>
      </span>

      {/* Mode */}
      <button
        className="hud-text cursor-pointer px-2 py-0.5 rounded"
        style={{
          background: 'var(--glow-cyan)',
          color: 'var(--accent-cyan)',
          border: '1px solid var(--border)',
        }}
        onClick={() => {
          const idx = modes.indexOf(mode)
          setMode(modes[(idx + 1) % modes.length])
        }}
      >
        {mode}
      </button>

      {/* Mesh */}
      <span className="hud-text">
        mesh:<span className="hud-value">{meshNodes.length}</span>
      </span>

      <div className="flex-1" />

      {/* Connection indicators */}
      <span className="hud-text flex items-center gap-1">
        api <StatusDot status={apiStatus} />
      </span>
      <span className="hud-text flex items-center gap-1">
        ws <StatusDot status={wsStatus} />
      </span>
      <span className="hud-text flex items-center gap-1">
        voice <StatusDot status={voiceStatus} />
      </span>

      {/* Mic status */}
      <span className="hud-text flex items-center gap-1.5">
        {micState === 'listening' ? '🎤' : '🎤'}
        <AudioMeter level={audioLevel} />
      </span>
    </footer>
  )
}
