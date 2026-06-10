import clsx from 'clsx'
import { useVisionStore, type VisionChainStatus } from '../../stores/visionStore'
import { getVisionClient } from '../../hooks/useVisionConnection'

const STATUS_CONFIG: Record<VisionChainStatus, { color: string; label: string }> = {
  relay_offline:        { color: 'bg-danger',   label: 'relay offline' },
  authenticating:       { color: 'bg-warn',     label: 'authenticating' },
  connected_no_frames:  { color: 'bg-warn',     label: 'connected — no frames' },
  beast_offline:        { color: 'bg-danger',   label: 'beast offline' },
  camera_unavailable:   { color: 'bg-danger',   label: 'camera unavailable' },
  stream_stale:         { color: 'bg-warn',     label: 'stream stale' },
  healthy:              { color: 'bg-ok',        label: 'healthy' },
  degraded:             { color: 'bg-warn',     label: 'degraded' },
  relay_idle:           { color: 'bg-muted',    label: 'relay idle' },
}

function formatAge(ms: number): string {
  if (ms < 0) return 'never'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
}

export function VisionConnectionStatus(): JSX.Element {
  const connected = useVisionStore((s) => s.connected)
  const health = useVisionStore((s) => s.chainHealth)
  const analysisStatus = useVisionStore((s) => s.analysisStatus)

  const cfg = connected
    ? STATUS_CONFIG[health.status] || STATUS_CONFIG.degraded
    : STATUS_CONFIG.relay_offline

  const handleReconnect = () => {
    const client = getVisionClient()
    if (!client) return
    client.reconnect()
  }

  const handleRestartCamera = () => {
    const client = getVisionClient()
    if (!client) return
    client.restartCamera()
  }

  const handleRefresh = () => {
    const client = getVisionClient()
    if (!client) return
    client.refreshCapabilities()
  }

  const showRecoveryActions = connected && health.status !== 'healthy'
  const showReconnect = !connected || health.status === 'relay_offline'
  const showRestartCamera = connected && (health.status === 'stream_stale' || health.status === 'connected_no_frames' || health.status === 'camera_unavailable')
  const showRefresh = connected && (health.status === 'degraded' || health.status === 'relay_idle')

  return (
    <div className="space-y-1">
      {/* Primary status line */}
      <div className="flex items-center gap-2 text-[10px] font-mono text-text-tertiary">
        <span className={clsx('w-1.5 h-1.5 rounded-full', cfg.color)} />
        <span>{cfg.label}</span>
        {health.frameFps > 0 && (
          <span className="text-text-quaternary ml-1">{health.frameFps} fps</span>
        )}
        {analysisStatus !== 'idle' && (
          <span className="text-cyan ml-auto">{analysisStatus}</span>
        )}
      </div>

      {/* Chain detail — shown when not healthy */}
      {connected && health.status !== 'healthy' && (
        <div className="px-2 py-1 rounded bg-surface-secondary text-[9px] font-mono text-text-tertiary space-y-0.5">
          <div className="flex gap-2">
            <span className={health.relayRunning ? 'text-ok' : 'text-danger'}>
              relay:{health.relayRunning ? 'up' : 'down'}
            </span>
            <span className={health.beastConnected ? 'text-ok' : 'text-danger'}>
              beast:{health.beastConnected ? 'up' : 'down'}
            </span>
            <span className={health.cameraStreaming ? 'text-ok' : 'text-danger'}>
              cam:{health.cameraStreaming ? 'live' : 'off'}
            </span>
          </div>
          {health.lastFrameAgeMs > 0 && (
            <div>last frame: {formatAge(health.lastFrameAgeMs)} ago</div>
          )}
          {health.blockers.length > 0 && (
            <div className="text-warn">
              {health.blockers.map((b, i) => <div key={i}>{b}</div>)}
            </div>
          )}
          {health.recoveryAction && (
            <div className="text-cyan">{health.recoveryAction}</div>
          )}
        </div>
      )}

      {/* Recovery actions */}
      {(showRecoveryActions || showReconnect) && (
        <div className="flex gap-1">
          {showReconnect && (
            <button
              onClick={handleReconnect}
              className="px-2 py-0.5 rounded bg-surface-secondary text-[9px] font-mono text-text-tertiary hover:bg-surface-tertiary"
            >
              reconnect
            </button>
          )}
          {showRestartCamera && (
            <button
              onClick={handleRestartCamera}
              className="px-2 py-0.5 rounded bg-surface-secondary text-[9px] font-mono text-text-tertiary hover:bg-surface-tertiary"
            >
              restart camera
            </button>
          )}
          {showRefresh && (
            <button
              onClick={handleRefresh}
              className="px-2 py-0.5 rounded bg-surface-secondary text-[9px] font-mono text-text-tertiary hover:bg-surface-tertiary"
            >
              refresh
            </button>
          )}
        </div>
      )}
    </div>
  )
}
