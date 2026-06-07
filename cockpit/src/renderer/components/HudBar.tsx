import { useState, useCallback } from 'react'
import { clsx } from 'clsx'
import { Radio } from 'lucide-react'
import { useSystemStore } from '../stores/systemStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { useVoiceStore } from '../stores/voiceStore'
import { useRealtimeStore } from '../stores/realtimeStore'
import { usePolling } from '../hooks/usePolling'

function StatusDot({ status }: { status: 'connected' | 'connecting' | 'disconnected' }) {
  return (
    <span
      className={clsx(
        'block w-[6px] h-[6px] rounded-full shrink-0',
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

function OrganismMetrics() {
  const nodeMetrics = useRealtimeStore((s) => s.nodeMetrics)
  const online = Object.values(nodeMetrics).filter((m) => m.status === 'online')
  const total = Object.keys(nodeMetrics).length
  const cpuValues = online.map((m) => m.cpu).filter((v): v is number => v != null)
  const memValues = online.map((m) => m.memory).filter((v): v is number => v != null)
  const diskValues = online.map((m) => m.disk).filter((v): v is number => v != null)
  const avgCpu = cpuValues.length > 0 ? cpuValues.reduce((a, b) => a + b, 0) / cpuValues.length : null
  const avgMem = memValues.length > 0 ? memValues.reduce((a, b) => a + b, 0) / memValues.length : null
  const avgDisk = diskValues.length > 0 ? diskValues.reduce((a, b) => a + b, 0) / diskValues.length : null
  const gpuNode = online.find((m) => m.gpu != null)
  const gpuUtil = gpuNode?.gpu?.utilization ?? null

  return (
    <>
      <span className="wv-label">
        cpu <span className="text-cyan">{avgCpu != null ? `${avgCpu.toFixed(0)}%` : '—'}</span>
      </span>
      <span className="wv-label">
        ram <span className="text-cyan">{avgMem != null ? `${avgMem.toFixed(0)}%` : '—'}</span>
      </span>
      <span className="wv-label">
        disk <span className={clsx(
          avgDisk != null && avgDisk > 90 ? 'text-danger' : avgDisk != null && avgDisk > 75 ? 'text-warn' : 'text-cyan'
        )}>{avgDisk != null ? `${avgDisk.toFixed(0)}%` : '—'}</span>
      </span>
      {gpuUtil != null && (
        <span className="wv-label">
          gpu <span className="text-cyan">{gpuUtil.toFixed(0)}%</span>
        </span>
      )}
      <span className="wv-label">
        nodes <span className={clsx(online.length === total ? 'text-ok' : 'text-warn')}>{online.length}/{total}</span>
      </span>
    </>
  )
}

export function HudBar() {
  const pulse = useSystemStore((s) => s.pulse)
  const meshNodes = useSystemStore((s) => s.meshNodes)
  const fetchPulse = useSystemStore((s) => s.fetchPulse)
  const fetchMeshNodes = useSystemStore((s) => s.fetchMeshNodes)
  const apiStatus = useCockpitStore((s) => s.apiStatus)
  const wsStatus = useCockpitStore((s) => s.wsStatus)
  const voiceStatus = useCockpitStore((s) => s.voiceStatus)
  const micState = useVoiceStore((s) => s.micState)
  const audioLevel = useVoiceStore((s) => s.audioLevel)
  const lastTranscript = useVoiceStore((s) => s.lastTranscript)

  const [posture, setPosture] = useState<string>('')
  const [nodeCount, setNodeCount] = useState<number>(0)
  const [continuityState, setContinuityState] = useState<string>('')
  const [lifecycleMode, setLifecycleMode] = useState<string>('')
  const [profileModes, setProfileModes] = useState<string[]>([])
  const [presenceSource, setPresenceSource] = useState<string>('')
  const [sttAvailable, setSttAvailable] = useState<boolean>(false)
  const [ttsAvailable, setTtsAvailable] = useState<boolean>(false)

  usePolling(fetchPulse, 5000)
  usePolling(fetchMeshNodes, 15000)

  const fetchWorkstationMode = useCallback(async () => {
    try {
      const res = await fetch('/api/umh/workstation/mode-composite')
      const data = await res.json()
      if (data.ok) {
        const mc = data.mode_composite ?? {}
        setPosture(mc.effective_posture ?? '')
        setContinuityState(mc.continuity_state ?? '')
        setLifecycleMode(mc.lifecycle_mode ?? '')
        setProfileModes(mc.active_profile_modes ?? [])
      }
    } catch { /* silent */ }
    try {
      const res = await fetch('/api/umh/workstation/nodes')
      const data = await res.json()
      if (data.ok) setNodeCount(data.count ?? 0)
    } catch { /* silent */ }
    try {
      const res = await fetch('/api/umh/presence/capabilities')
      const data = await res.json()
      if (data.ok) {
        setSttAvailable(data.stt_available ?? false)
        setTtsAvailable(data.tts_available ?? false)
      }
    } catch { /* silent */ }
  }, [])

  usePolling(fetchWorkstationMode, 15000, true, 1000)

  const isOnline = apiStatus === 'connected' || wsStatus === 'connected'

  return (
    <footer
      className="flex items-center gap-4 px-3 select-none bg-surface border-t border-border"
      style={{ height: 'var(--spacing-hud-height)' }}
    >
      {/* Status cluster — fullscreen indicator + online */}
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1">
          <Radio size={12} className="text-cyan wv-pulse shrink-0" />
          <span className="wv-label leading-none">Full-Screen</span>
        </span>
        <span className="flex items-center gap-1">
          <div className={clsx('w-2 h-2 rounded-full shrink-0', isOnline ? 'bg-ok wv-pulse' : 'bg-danger')} />
          <span className="wv-label leading-none">{isOnline ? 'Online' : 'Offline'}</span>
        </span>
      </div>

      {/* Workstation posture */}
      {posture && (
        <span className={clsx(
          'text-[10px] font-mono px-2 py-1 rounded',
          posture === 'active' && 'bg-ok/10 text-ok',
          posture === 'deep_work' && 'bg-cyan/10 text-cyan',
          posture === 'remote' && 'bg-warn/10 text-warn',
          posture === 'overnight_autonomous' && 'bg-purple-500/10 text-purple-400',
          posture === 'inactive' && 'bg-surface text-text-tertiary',
        )}>{posture.toUpperCase()}</span>
      )}

      {/* Continuity state */}
      {continuityState && (
        <span className={clsx(
          'text-[10px] font-mono px-2 py-1 rounded',
          continuityState === 'active' && 'bg-ok/10 text-ok',
          continuityState === 'idle' && 'bg-surface text-text-tertiary',
          continuityState === 'away' && 'bg-warn/10 text-warn',
          continuityState === 'remote' && 'bg-cyan/10 text-cyan',
          continuityState === 'night_sleeping' && 'bg-purple-500/10 text-purple-400',
          continuityState === 'returning' && 'bg-ok/10 text-ok',
          continuityState === 'resume_brief' && 'bg-cyan/10 text-cyan',
        )}>{continuityState.replace(/_/g, ' ').toUpperCase()}</span>
      )}

      {/* Lifecycle mode */}
      {lifecycleMode && lifecycleMode !== 'day_cycle' && (
        <span className="text-[10px] font-mono px-2 py-1 rounded bg-warn/10 text-warn">
          {lifecycleMode.replace(/_/g, ' ').toUpperCase()}
        </span>
      )}

      {/* Profile modes */}
      {profileModes.length > 0 && (
        <span className="text-[10px] font-mono px-2 py-1 rounded bg-cyan/10 text-cyan">
          {profileModes.map(m => m.toUpperCase()).join(' + ')}
        </span>
      )}

      {/* Node count */}
      {nodeCount > 0 && (
        <span className="wv-label">
          nodes:<span className="text-cyan">{nodeCount}</span>
        </span>
      )}

      {/* Presence / voice capability */}
      <span className="wv-label flex items-center gap-1 leading-none">
        <StatusDot status={sttAvailable ? 'connected' : 'disconnected'} /> stt
      </span>
      <span className="wv-label flex items-center gap-1 leading-none">
        <StatusDot status={ttsAvailable ? 'connected' : 'disconnected'} /> tts
      </span>

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
      <OrganismMetrics />

      <span className="wv-label">
        mesh:<span className="text-cyan">{meshNodes.length}</span>
      </span>

      {/* Connection indicators */}
      <span className="wv-label flex items-center gap-1 leading-none">
        <StatusDot status={apiStatus} /> api
      </span>
      <span className="wv-label flex items-center gap-1 leading-none">
        <StatusDot status={wsStatus} /> ws
      </span>
      <span className="wv-label flex items-center gap-1 leading-none">
        <StatusDot status={voiceStatus} /> voice
      </span>

    </footer>
  )
}
