import { useState, useCallback } from 'react'
import { clsx } from 'clsx'
import { useSystemStore } from '../stores/systemStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { useVoiceStore } from '../stores/voiceStore'
import { usePolling } from '../hooks/usePolling'

function StatusDot({ status }: { status: 'connected' | 'connecting' | 'disconnected' }) {
  return (
    <span
      className={clsx(
        'inline-block w-[6px] h-[6px] rounded-full',
        status === 'connected' && 'bg-ok',
        status === 'connecting' && 'bg-warn',
        status === 'disconnected' && 'bg-danger',
      )}
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
            background: i < active ? 'var(--color-cyan)' : 'var(--color-border-active)',
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
  const activePanel = useCockpitStore((s) => s.activePanel)
  const apiStatus = useCockpitStore((s) => s.apiStatus)
  const wsStatus = useCockpitStore((s) => s.wsStatus)
  const voiceStatus = useCockpitStore((s) => s.voiceStatus)
  const micState = useVoiceStore((s) => s.micState)
  const audioLevel = useVoiceStore((s) => s.audioLevel)
  const lastTranscript = useVoiceStore((s) => s.lastTranscript)

  const [posture, setPosture] = useState<string>('')
  const [nodeCount, setNodeCount] = useState<number>(0)

  const fetchWorkstationMode = useCallback(async () => {
    try {
      const res = await fetch('/api/umh/workstation/mode-composite')
      const data = await res.json()
      if (data.ok) {
        setPosture(data.mode_composite?.effective_posture ?? '')
      }
    } catch { /* silent */ }
    try {
      const res = await fetch('/api/umh/workstation/nodes')
      const data = await res.json()
      if (data.ok) setNodeCount(data.count ?? 0)
    } catch { /* silent */ }
  }, [])

  usePolling(fetchWorkstationMode, 15000)

  const modes = ['EXECUTE', 'PLAN', 'REVIEW'] as const

  return (
    <footer
      className="flex items-center gap-4 px-3 select-none bg-surface border-t border-border"
      style={{ height: 'var(--spacing-hud-height)' }}
    >
      {/* Mode badge */}
      <button
        className="wv-badge wv-badge-cyan cursor-pointer"
        onClick={() => {
          const idx = modes.indexOf(mode)
          setMode(modes[(idx + 1) % modes.length])
        }}
      >
        {mode}
      </button>

      {/* Workstation posture */}
      {posture && (
        <span className={clsx(
          'text-[10px] font-mono px-1.5 py-0.5 rounded',
          posture === 'active' && 'bg-ok/10 text-ok',
          posture === 'deep_work' && 'bg-cyan/10 text-cyan',
          posture === 'remote' && 'bg-warn/10 text-warn',
          posture === 'overnight_autonomous' && 'bg-purple-500/10 text-purple-400',
          posture === 'inactive' && 'bg-surface text-text-tertiary',
        )}>{posture.toUpperCase()}</span>
      )}

      {/* Node count */}
      {nodeCount > 0 && (
        <span className="wv-label">
          nodes:<span className="text-cyan">{nodeCount}</span>
        </span>
      )}

      {/* Active route */}
      <span className="wv-label">{activePanel}</span>

      {/* Voice transcript ticker */}
      {micState !== 'idle' && (
        <span className="flex items-center gap-2 flex-1 min-w-0">
          <AudioMeter level={audioLevel} />
          <span className="font-mono text-[11px] text-text-secondary truncate">
            {lastTranscript || (micState === 'listening' ? 'listening...' : 'processing...')}
          </span>
        </span>
      )}

      {micState === 'idle' && <div className="flex-1" />}

      {/* System metrics */}
      <span className="wv-label flex items-center gap-1.5">
        <StatusDot status={pulse && pulse.active_agents > 0 ? 'connected' : 'disconnected'} />
        <span className="text-cyan">{pulse?.active_agents ?? 0}</span> agents
      </span>

      <span className="wv-label">
        cpu <span className="text-cyan">{pulse?.cpu_percent?.toFixed(0) ?? '—'}%</span>
      </span>

      <span className="wv-label">
        ram <span className="text-cyan">{pulse?.memory_percent?.toFixed(0) ?? '—'}%</span>
      </span>

      <span className="wv-label">
        mesh:<span className="text-cyan">{meshNodes.length}</span>
      </span>

      {/* Connection indicators */}
      <span className="wv-label flex items-center gap-1">
        api <StatusDot status={apiStatus} />
      </span>
      <span className="wv-label flex items-center gap-1">
        ws <StatusDot status={wsStatus} />
      </span>
      <span className="wv-label flex items-center gap-1">
        voice <StatusDot status={voiceStatus} />
      </span>
    </footer>
  )
}
